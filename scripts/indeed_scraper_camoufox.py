#!/usr/bin/env python3
"""
Indeed Job Scraper - ENHANCED VERSION with Checkpointing
Version 2.0 - Supports large-scale scraping (1000+ jobs) with automatic resume
"""

import os
import time
import random
import asyncio
import logging
import pandas as pd
from datetime import datetime
from camoufox import AsyncCamoufox
from bs4 import BeautifulSoup
import re
import glob
from urllib.parse import urljoin, quote_plus

# Import the captcha solving library
from camoufox_captcha import solve_captcha

# Set up logging
logging.basicConfig(
    level='INFO',
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Configuration
DEFAULT_POSITION = "python analyst"
DEFAULT_LOCATION = "remote"
DEFAULT_MAX_JOBS = 1000
DEFAULT_DELAY_MIN = 3
DEFAULT_DELAY_MAX = 8
CHECKPOINT_FREQUENCY = 50  # Save every 50 jobs


def get_checkpoint_filename(position, location, timestamp):
    """Generate checkpoint filename with timestamp and search parameters"""
    # Clean parameters for filename
    clean_position = re.sub(r'[^\w\s-]', '', position).strip().replace(' ', '_')
    clean_location = re.sub(r'[^\w\s-]', '', location).strip().replace(' ', '_')
    
    filename = f"checkpoint_{timestamp}_{clean_position}_{clean_location}.csv"
    return filename


def find_existing_checkpoint(position, location):
    """
    Find existing checkpoint files for the given search parameters.
    Returns the most recent checkpoint file and the number of jobs already scraped.
    """
    # Clean parameters for matching
    clean_position = re.sub(r'[^\w\s-]', '', position).strip().replace(' ', '_')
    clean_location = re.sub(r'[^\w\s-]', '', location).strip().replace(' ', '_')
    
    # Find all checkpoint files matching this search
    pattern = f"checkpoint_*_{clean_position}_{clean_location}.csv"
    checkpoint_files = glob.glob(pattern)
    
    if not checkpoint_files:
        return None, 0
    
    # Get the most recent checkpoint
    latest_checkpoint = max(checkpoint_files, key=os.path.getctime)
    
    # Load to get job count
    try:
        df = pd.read_csv(latest_checkpoint)
        jobs_completed = len(df)
        print(f"\n[CHECKPOINT FOUND] {latest_checkpoint}")
        print(f"   Jobs already scraped: {jobs_completed}")
        return latest_checkpoint, jobs_completed
    except Exception as e:
        print(f"\n[WARNING] Error reading checkpoint file: {e}")
        return None, 0


def save_checkpoint(dataframe, position, location, timestamp, job_count):
    """Save checkpoint with current progress"""
    checkpoint_file = get_checkpoint_filename(position, location, timestamp)
    dataframe.to_csv(checkpoint_file, index=False)
    print(f"\n[CHECKPOINT SAVED] {checkpoint_file} ({job_count} jobs)")


def cleanup_checkpoints(position, location):
    """Delete checkpoint files after successful completion"""
    clean_position = re.sub(r'[^\w\s-]', '', position).strip().replace(' ', '_')
    clean_location = re.sub(r'[^\w\s-]', '', location).strip().replace(' ', '_')
    
    pattern = f"checkpoint_*_{clean_position}_{clean_location}.csv"
    checkpoint_files = glob.glob(pattern)
    
    for checkpoint in checkpoint_files:
        try:
            os.remove(checkpoint)
            print(f"[CLEANUP] Removed checkpoint: {checkpoint}")
        except Exception as e:
            print(f"[WARNING] Could not delete {checkpoint}: {e}")


def extract_salary_with_regex(text):
    """Extract salary information from text using regex patterns."""
    if not text or text == 'N/A':
        return 'N/A'
    
    patterns = [
        r'\$[\d,]+\s*-\s*\$[\d,]+(?:\s*(?:a year|per year|annually|/year|/yr))?',
        r'\$[\d,]+(?:\s*(?:a year|per year|annually|/year|/yr))',
        r'\$[\d,]+\s*-\s*\$[\d,]+(?:\s*(?:per hour|an hour|/hour|/hr))',
        r'\$[\d,]+(?:\s*(?:per hour|an hour|/hour|/hr))',
        r'[\d,]+\s*-\s*[\d,]+\s*(?:USD|dollars?)?\s*(?:a year|per year|annually|/year)',
        r'(?:salary|compensation|pay)[\s:]*\$[\d,]+\s*-\s*\$[\d,]+',
        r'(?:up to|as much as)\s*\$[\d,]+(?:K|k)?',
        r'\$\d+K?\s*-\s*\$\d+K?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            salary_text = match.group(0).strip()
            salary_text = re.sub(r'\s+', ' ', salary_text)
            return salary_text
    
    return 'N/A'


async def random_delay(min_seconds=2, max_seconds=5):
    """Add a random delay to mimic human behavior"""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)


def print_indeed_splash():
    """Print Indeed scraper splash screen"""
    print("=" * 80)
    print("=" * 80)
    print("||" + " " * 76 + "||")
    print("||" + " " * 21 + "INDEED JOB SCRAPER - ENHANCED v2.0" + " " * 19 + "||")
    print("||" + " " * 76 + "||")
    print("||" + " " * 18 + "Automatic Checkpointing & Resume" + " " * 26 + "||")
    print("||" + " " * 17 + "Enhanced Salary Extraction" + " " * 30 + "||")
    print("||" + " " * 76 + "||")
    print("=" * 80)
    print("=" * 80)
    print("")


def get_indeed_url(position, location):
    """Generate Indeed search URL"""
    base_url = "https://www.indeed.com/jobs"
    position_encoded = quote_plus(position)
    location_encoded = quote_plus(location)
    url = f"{base_url}?q={position_encoded}&l={location_encoded}"
    return url


async def handle_cookie_consent(page):
    """Check for and handle cookie consent dialogs on Indeed"""
    try:
        page_content = await page.content()
        cookie_indicators = [
            'accept all', 'accept cookies', 'cookie consent', 'cookies policy',
            'we use cookies', 'cookie notice', 'privacy notice', 'accept all cookies',
            'onetrust', 'cookie banner', 'cookie preferences'
        ]
        
        if any(indicator in page_content.lower() for indicator in cookie_indicators):
            print("Cookie consent dialog detected - handling...")
            
            accept_selectors = [
                'button#onetrust-accept-btn-handler',
                '#onetrust-accept-btn-handler',
                'button:has-text("Accept All")',
                'button:has-text("Accept all")',
                '[id*="accept"]:has-text("Accept All")',
            ]
            
            for selector in accept_selectors:
                try:
                    accept_button = await page.query_selector(selector)
                    if accept_button:
                        await accept_button.click()
                        await asyncio.sleep(2)
                        return True
                except Exception:
                    continue
        
        return False
        
    except Exception as e:
        logging.warning(f"Cookie consent check error: {e}")
        return False


async def check_and_handle_cloudflare(page):
    """Check for and handle Cloudflare challenges on Indeed"""
    try:
        page_content = await page.content()
        
        cloudflare_indicators = [
            'cloudflare', 'checking your browser', 'just a moment', 'please wait',
            'verify you are human', 'challenge', 'security check'
        ]
        
        if any(indicator in page_content.lower() for indicator in cloudflare_indicators):
            print("Cloudflare challenge detected - attempting automatic resolution...")
            
            try:
                await solve_captcha(page, captcha_type='cloudflare', challenge_type='interstitial')
                print("Cloudflare challenge solved!")
                await asyncio.sleep(5)
                await handle_cookie_consent(page)
                return True
                    
            except Exception:
                print("Waiting for automatic Cloudflare resolution...")
                await asyncio.sleep(15)
                return True
        
        return False
        
    except Exception as e:
        logging.warning(f"Cloudflare check error: {e}")
        return False


async def extract_job_data_enhanced(page, job_element):
    """Enhanced job data extraction with improved salary detection."""
    try:
        job_html = await job_element.inner_html()
        soup = BeautifulSoup(job_html, 'html.parser')
        
        # Extract job title
        title_elem = soup.find('h2', class_='jobTitle')
        if not title_elem:
            title_elem = soup.find('a', class_='jcs-JobTitle')
        title = title_elem.get_text(strip=True) if title_elem else 'N/A'
        
        # Extract company name
        company_elem = soup.find('span', {'data-testid': 'company-name'})
        if not company_elem:
            company_elem = soup.find('span', class_='companyName')
        company = company_elem.get_text(strip=True) if company_elem else 'N/A'
        
        # Extract location
        location_elem = soup.find('div', {'data-testid': 'text-location'})
        if not location_elem:
            location_elem = soup.find('div', class_='companyLocation')
        location = location_elem.get_text(strip=True) if location_elem else 'N/A'
        
        # Extract rating
        rating_elem = soup.find('span', class_='ratingNumber')
        rating = rating_elem.get_text(strip=True) if rating_elem else 'N/A'
        
        # Extract date
        date_elem = soup.find('span', {'data-testid': 'myJobsStateDate'})
        if not date_elem:
            date_elem = soup.find('span', class_='date')
        date = date_elem.get_text(strip=True) if date_elem else 'N/A'
        
        # ENHANCED SALARY EXTRACTION
        salary = 'N/A'
        salary_selectors = [
            ('div', {'data-testid': 'attribute_snippet_testid'}),
            ('div', {'class': 'salary-snippet-container'}),
            ('div', {'class': 'salary-snippet'}),
            ('div', {'class': 'metadata'}),
            ('span', {'class': 'salary'}),
        ]
        
        for tag, attrs in salary_selectors:
            salary_elem = soup.find(tag, attrs)
            if salary_elem:
                salary_text = salary_elem.get_text(strip=True)
                if salary_text and '$' in salary_text:
                    salary = salary_text
                    break
        
        if salary == 'N/A':
            job_card_text = soup.get_text()
            salary = extract_salary_with_regex(job_card_text)
        
        # Extract description
        desc_elem = soup.find('div', class_='job-snippet')
        if not desc_elem:
            desc_elem = soup.find('div', {'data-testid': 'job-snippet'})
        description = desc_elem.get_text(strip=True) if desc_elem else 'N/A'
        
        # Extract link
        link_elem = soup.find('a', class_='jcs-JobTitle')
        if not link_elem:
            link_elem = soup.find('a', href=re.compile(r'/rc/clk\?jk='))
        if not link_elem:
            link_elem = soup.find('a', href=re.compile(r'/viewjob\?jk='))
        
        if link_elem and link_elem.get('href'):
            link = urljoin('https://www.indeed.com', link_elem['href'])
        else:
            link = 'NaN'
        
        return {
            'Title': title,
            'Company': company,
            'Location': location,
            'Rating': rating,
            'Date': date,
            'Salary': salary,
            'Description': description,
            'Links': link
        }
        
    except Exception as e:
        logging.error(f"Error extracting job data: {e}")
        return None


async def scrape_full_job_description_enhanced(page, job_url, current_salary):
    """Scrape full job description AND try to get salary if not found yet."""
    try:
        await page.goto(job_url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(random.uniform(2, 4))
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract full description
        desc_elem = soup.find('div', id='jobDescriptionText')
        if not desc_elem:
            desc_elem = soup.find('div', class_='jobsearch-jobDescriptionText')
        
        description = desc_elem.get_text(separator='\n', strip=True) if desc_elem else 'Description not found'
        
        # Enhanced salary search
        enhanced_salary = current_salary
        if current_salary == 'N/A' or not current_salary or current_salary == 'NaN':
            salary_selectors = [
                ('div', {'data-testid': 'job-salary'}),
                ('div', {'class': 'js-match-insights-provider-salary'}),
                ('div', {'class': 'jobsearch-JobMetadataHeader-item'}),
            ]
            
            for tag, attrs in salary_selectors:
                salary_elem = soup.find(tag, attrs)
                if salary_elem:
                    salary_text = salary_elem.get_text(strip=True)
                    if salary_text and '$' in salary_text:
                        enhanced_salary = salary_text
                        break
            
            if enhanced_salary == 'N/A' and desc_elem:
                desc_text = desc_elem.get_text()
                enhanced_salary = extract_salary_with_regex(desc_text)
        
        return description, enhanced_salary
            
    except Exception as e:
        logging.error(f"Error scraping full description: {e}")
        return 'Error retrieving description', current_salary


async def scrape_indeed_jobs(position=DEFAULT_POSITION, location=DEFAULT_LOCATION, max_jobs=DEFAULT_MAX_JOBS, scrape_full_descriptions=True):
    """Main function to scrape Indeed jobs with checkpointing support"""
    print_indeed_splash()
    
    # Check for existing checkpoint
    checkpoint_file, jobs_completed = find_existing_checkpoint(position, location)
    
    # Generate timestamp for this run
    run_timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    
    # Load checkpoint or create new dataframe
    if checkpoint_file and jobs_completed > 0:
        print(f"\n[RESUME] Continuing from checkpoint...")
        dataframe = pd.read_csv(checkpoint_file)
        start_index = jobs_completed
        print(f"   Will continue from job #{start_index + 1}")
    else:
        print(f"\n[NEW] Starting new scrape...")
        dataframe = pd.DataFrame(columns=["Title", "Company", "Location", "Rating", "Date", "Salary", "Description", "Links"])
        start_index = 0
    
    jn = start_index
    start_time = datetime.now()
    
    print(f"\nSearch: '{position}' in '{location}'")
    print(f"Target: {max_jobs} total jobs")
    print(f"Starting from: Job #{start_index + 1}")
    print("=" * 80)
    
    browser_options = {
        'headless': False,
        'humanize': True,
        'geoip': False,
        'i_know_what_im_doing': True,
        'config': {'forceScopeAccess': True},
        'disable_coop': True
    }
    
    async with AsyncCamoufox(**browser_options) as browser:
        page = await browser.new_page()
        print("\nBrowser initialized with Enhanced Salary Detection + Checkpointing")
        
        search_url = get_indeed_url(position, location)
        print(f"Starting URL: {search_url}\n")
        
        # Calculate starting page (10 jobs per page)
        start_page = (start_index // 10) * 10

        # Calculate total pages needed
        pages_needed = (max_jobs + 9) // 10  # Round up
        end_page = pages_needed * 10
        
        for i in range(start_page, end_page, 10):
            try:
                current_url = search_url + "&start=" + str(i)
                
                print(f"Page {(i//10)+1} - Loading...")
                await page.goto(current_url, wait_until='networkidle')
                await random_delay(3, 5)
                
                await check_and_handle_cloudflare(page)
                await handle_cookie_consent(page)
                
                job_elements = await page.query_selector_all('.job_seen_beacon')
                
                if not job_elements:
                    job_elements = await page.query_selector_all('[data-testid="job-card"]')
                    if not job_elements:
                        job_elements = await page.query_selector_all('.slider_container .slider_item')
                
                if not job_elements:
                    print("No jobs found on this page - ending scrape")
                    break
                
                print(f"Found {len(job_elements)} job elements")
                
                for job_element in job_elements:
                    if jn >= max_jobs:
                        break
                    
                    # Skip jobs we already have
                    if jn < start_index:
                        jn += 1
                        continue
                    
                    try:
                        job_data = await extract_job_data_enhanced(page, job_element)
                        if job_data:
                            jn += 1
                            dataframe = pd.concat([dataframe, pd.DataFrame([job_data])], ignore_index=True)
                            
                            salary_indicator = "[$]" if job_data['Salary'] != 'N/A' else ""
                            print(f"  Job #{jn:4d} added - {job_data['Title'][:50]} {salary_indicator}")
                            
                            # CHECKPOINT SAVE every 50 jobs
                            if jn % CHECKPOINT_FREQUENCY == 0:
                                save_checkpoint(dataframe, position, location, run_timestamp, jn)
                                print(f"  [PROGRESS] {jn}/{max_jobs} jobs ({(jn/max_jobs)*100:.1f}%)")
                            
                            await random_delay(1, 2)
                    
                    except Exception as e:
                        logging.error(f"Error processing job: {e}")
                        continue
                
                if jn >= max_jobs:
                    print(f"\n[COMPLETE] Reached target of {max_jobs} jobs")
                    break
                
                await random_delay(5, 8)
                
            except Exception as e:
                logging.error(f"Error on page: {e}")
                # Save checkpoint even on error
                save_checkpoint(dataframe, position, location, run_timestamp, jn)
                break
        
        # Scrape full descriptions if requested
        if scrape_full_descriptions and len(dataframe) > 0:
            print(f"\n{'='*80}")
            print(f"Scraping full descriptions for {len(dataframe)} jobs...")
            print(f"{'='*80}\n")
            
            links_list = dataframe['Links'].tolist()
            salaries_list = dataframe['Salary'].tolist()
            descriptions = []
            enhanced_salaries = []
            indices_to_remove = []
            
            for index, (link, current_salary) in enumerate(zip(links_list, salaries_list)):
                if link != 'NaN' and link != '':
                    try:
                        print(f"Description {index+1}/{len(links_list)}: {dataframe.iloc[index]['Title'][:40]}")
                        full_desc, enhanced_salary = await scrape_full_job_description_enhanced(page, link, current_salary)
                        descriptions.append(full_desc)
                        enhanced_salaries.append(enhanced_salary)
                        
                        if enhanced_salary != 'N/A' and enhanced_salary != current_salary:
                            print(f"  [$] Found salary: {enhanced_salary}")
                        
                        # Save checkpoint every 50 descriptions
                        if (index + 1) % CHECKPOINT_FREQUENCY == 0:
                            temp_df = dataframe.copy()
                            if len(descriptions) == len(temp_df):
                                temp_df['Description'] = descriptions
                                temp_df['Salary'] = enhanced_salaries
                            save_checkpoint(temp_df, position, location, run_timestamp, jn)
                        
                        await random_delay(3, 6)
                        
                    except Exception as e:
                        logging.error(f"Error scraping description {index+1}: {e}")
                        indices_to_remove.append(index)
                        continue
                else:
                    indices_to_remove.append(index)
                    continue
            
            # Remove failed jobs
            mask = ~dataframe.index.isin(indices_to_remove)
            dataframe = dataframe[mask].copy()
            
            # Align arrays
            if len(descriptions) != len(dataframe):
                if len(descriptions) < len(dataframe):
                    descriptions += [''] * (len(dataframe) - len(descriptions))
                    enhanced_salaries += ['N/A'] * (len(dataframe) - len(enhanced_salaries))
                else:
                    descriptions = descriptions[:len(dataframe)]
                    enhanced_salaries = enhanced_salaries[:len(dataframe)]
            
            dataframe['Description'] = descriptions
            dataframe['Salary'] = enhanced_salaries
    
    # Save final results
    if len(dataframe) > 0:
        date = datetime.today().strftime('%Y-%m-%d_%H-%M')
        csv_filename = date + "_" + position + "_" + location + ".csv"
        dataframe.to_csv(csv_filename, index=False)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        jobs_with_salary = (dataframe['Salary'] != 'N/A').sum()
        salary_percentage = (jobs_with_salary / len(dataframe)) * 100
        
        print("\n" + "=" * 80)
        print("SCRAPING COMPLETED!")
        print("=" * 80)
        print(f"Total jobs scraped: {len(dataframe)}")
        print(f"Jobs with salary info: {jobs_with_salary} ({salary_percentage:.1f}%)")
        print(f"Time taken: {duration}")
        print(f"Final results saved to: {csv_filename}")
        print("=" * 80)
        
        # Cleanup checkpoints
        print("\nCleaning up checkpoint files...")
        cleanup_checkpoints(position, location)
        
        print("\n[SUCCESS] All done!")
    
    else:
        print("\n[WARNING] No jobs were scraped.")
    
    return dataframe


async def main():
    """Main entry point with configuration"""
    import sys
    
    position = DEFAULT_POSITION
    locations = DEFAULT_LOCATION
    postings = DEFAULT_MAX_JOBS
    
    if len(sys.argv) > 1:
        position = sys.argv[1]
    if len(sys.argv) > 2:
        locations = sys.argv[2]
    if len(sys.argv) > 3:
        postings = int(sys.argv[3])
    
    dataframe = await scrape_indeed_jobs(
        position=position,
        location=locations,
        max_jobs=postings,
        scrape_full_descriptions=True
    )
    
    return dataframe


if __name__ == "__main__":
    asyncio.run(main())
