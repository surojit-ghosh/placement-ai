import requests
from bs4 import BeautifulSoup
import re
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

URL = "https://www.naukri.com/job-listings-service-desk-engineer-wipro-kolkata-pune-bengaluru-0-to-4-years-260225017321?src=drecomm_profile&sid=17422879425688541&xp=1&px=1"

def clean_text(text):
    if text:
        return re.sub(r'\s+', ' ', text).strip()
    return None

def extract_skills(soup):
    skills = []
    # Updated skill selectors
    skills_section = soup.find('div', {'class': lambda x: x and ('key-skill' in x.lower() or 'skills' in x.lower())})
    if skills_section:
        skill_spans = skills_section.find_all(['span', 'div'], {'class': lambda x: x and ('chip' in x.lower() or 'skill' in x.lower())})
        for skill in skill_spans:
            clean_skill = clean_text(skill.text)
            if clean_skill:
                skills.append(clean_skill)
    return skills

def extract_job_details(soup, url):
    """Extract job details from the BeautifulSoup object"""
    
    job_details = {
        "title": None,
        "company": None,
        "experience": None,
        "salary": None,
        "location": None,
        "posted_date": None,
        "job_description": None,
        "skills": [],
        "education": None,
        "role": None,
        "industry_type": None,
        "employment_type": None,
        "job_functions": [],
        "url": url
    }
    
    # Extract title with flexible class matching
    title_element = soup.find('h1', {'class': lambda x: x and ('jd-header-title' in x.lower())})
    if title_element:
        job_details["title"] = clean_text(title_element.text)
    
    # Extract company with multiple possible selectors
    company_element = (
        soup.find('a', {'class': lambda x: x and 'company-name' in x.lower()}) or
        soup.find('div', {'class': lambda x: x and 'company-name' in x.lower()})
    )
    if company_element:
        job_details["company"] = clean_text(company_element.text)
    
    # Extract experience, salary, location
    info_elements = soup.find_all(['span', 'div'], {'class': lambda x: x and (
        'experience-container' in x.lower() or
        'salary-container' in x.lower() or
        'location-container' in x.lower() or
        'icon-text' in x.lower()
    )})
    
    for element in info_elements:
        text = clean_text(element.text)
        if text:
            if any(exp in text.lower() for exp in ['year', 'yr', 'experience']):
                job_details["experience"] = text
            elif any(sal in text.lower() for sal in ['pa', 'lpa', 'salary']):
                job_details["salary"] = text
            elif any(loc in text.lower() for loc in ['location', 'based']):
                job_details["location"] = text
    
    # Extract posted date
    posted_date = soup.find(['span', 'div'], {'class': lambda x: x and 'posted' in x.lower()})
    if posted_date:
        job_details["posted_date"] = clean_text(posted_date.text)
    
    # Extract job description
    jd_element = soup.find('div', {'class': lambda x: x and ('job-desc' in x.lower() or 'jd-desc' in x.lower())})
    if jd_element:
        job_details["job_description"] = clean_text(jd_element.text)
    
    # Extract skills
    job_details["skills"] = extract_skills(soup)
    
    # Extract other details
    details_section = soup.find_all(['div', 'section'], {'class': lambda x: x and 'details' in x.lower()})
    for section in details_section:
        labels = section.find_all(['label', 'div'], {'class': lambda x: x and ('label' in x.lower() or 'key' in x.lower())})
        for label in labels:
            label_text = clean_text(label.text).lower()
            value = label.find_next(['span', 'div'], {'class': lambda x: x and ('value' in x.lower() or 'info' in x.lower())})
            
            if value:
                value_text = clean_text(value.text)
                if 'role' in label_text:
                    job_details["role"] = value_text
                elif 'industry' in label_text:
                    job_details["industry_type"] = value_text
                elif 'employment' in label_text:
                    job_details["employment_type"] = value_text
                elif 'education' in label_text:
                    job_details["education"] = value_text
                elif 'functional area' in label_text:
                    job_details["job_functions"] = [func.strip() for func in value_text.split(',')]
    
    return job_details

async def scrape_job(job_url):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    driver = None
    try:
        print("Initializing Chrome WebDriver...")
        # Removed version parameter from ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        print(f"Navigating to URL: {job_url}")
        driver.get(job_url)
        
        # Add explicit waits with increased timeout
        wait = WebDriverWait(driver, 30)
        print("Waiting for page to load...")
        
        # Wait for page load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        
        # Additional wait for dynamic content
        await asyncio.sleep(5)
        
        try:
            # Wait for job title
            title_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1[class*='jd-header-title']"))
            )
            print(f"Found title: {title_element.text}")
        except Exception as e:
            print(f"Warning: Could not find title element: {str(e)}")
        
        # Get page source after JS execution
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Save HTML for debugging
        try:
            with open('debug_page.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
        except Exception as e:
            print(f"Warning: Could not save debug page: {str(e)}")
        
        return extract_job_details(soup, job_url)
        
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
        if driver:
            try:
                with open('error_page.html', 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
            except:
                print("Could not save error page")
        return None
        
    finally:
        try:
            if driver:
                driver.quit()
        except:
            print("Error closing driver")

if __name__ == "__main__":
    try:
        print("Starting scraper...")
        data = asyncio.run(scrape_job(URL))
        if data:
            print("\nExtracted Data:")
            for key, value in data.items():
                print(f"{key}: {value}")
        else:
            print("Failed to extract data")
    except Exception as e:
        print(f"Main execution error: {str(e)}")