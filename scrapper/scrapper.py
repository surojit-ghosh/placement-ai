from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import asyncio
import re
import html2text
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def clean_text(text):
    if text:
        return re.sub(r'\s+', ' ', text).strip()
    return None


def extract_job_details(soup, url):
    job_details = {
        "title": None,
        "company": None,
        "experience": None,
        "salary": None,
        "location": None,
        "job_description": None,
        "skills": [],
        "role": None,
        "industry_type": None,
        "employment_type": None,
        "url": url
    }

    # Title
    title_element = soup.find('h1', {'class': lambda x: x and ('jd-header-title' in x.lower())})
    if title_element:
        job_details["title"] = clean_text(title_element.text)

    # Company
    company_element = soup.find('div', {'class': lambda x: x and ('jd-header-comp-name' in x.lower())})
    if company_element:
        a_tag = company_element.find('a')
        if a_tag:
            job_details["company"] = clean_text(a_tag.text)

    experience_salary_container_element = soup.find('div', {'class': lambda x: x and ('exp-salary-container' in x.lower())})
    
    # Experience
    experience_element = experience_salary_container_element.find('div', {'class': lambda x: x and ('exp') in x.lower()})
    if experience_element:
        span_element = experience_element.find('span')
        if span_element:
            job_details["experience"] = clean_text(span_element.text)

    # Salary
    salary_element = experience_salary_container_element.find('div', {'class': lambda x: x and ('salary') in x.lower()})
    if salary_element:
        span_element = salary_element.find('span')
        if span_element:
            job_details["salary"] = clean_text(span_element.text)

    # Location
    location_element = soup.find('span', {'class': lambda x: x and ('location') in x.lower()})
    if location_element:
        location_links = location_element.find_all('a')
        if location_links:
            for link in location_links:
                if job_details["location"] is None:
                    job_details["location"] = clean_text(link.text)
                else:
                    job_details["location"] += f", {clean_text(link.text)}"

    # Job Description
    job_description_element = soup.find('section', {'class': lambda x: x and ('job-desc-container') in x.lower()})
    job_desc = html2text.html2text(str(job_description_element))
    cleaned_text = re.sub(r'Role: .*', '', job_desc, flags=re.DOTALL).strip()
    job_details["job_description"] = cleaned_text

    # Skills
    skills = []
    skills_section = soup.find('div', {'class': lambda x: x and ('key-skill' in x.lower() or 'skills' in x.lower())})
    skills_divs = skills_section.find_all('div')
    if skills_divs[2]:
        skills_a = skills_divs[2].find_all('a')
        for skill in skills_a:
            skills.append(clean_text(skill.text))

    if skills_divs[3]:
        skills_a = skills_divs[3].find_all('a')
        for skill in skills_a:
            skills.append(clean_text(skill.text))

    job_details["skills"] = skills

    other_elements = soup.find('div', {'class': lambda x: x and ('other-details') in x.lower()}).find_all('div')
    # Role
    role_element = other_elements[0].find('span')
    if role_element:
        a_element = role_element.find('a')
        job_details["role"] = clean_text(a_element.text)

    # Industry Type
    industry_element = other_elements[1].find('span')
    if industry_element:
        a_element = industry_element.find('a')
        job_details["industry_type"] = clean_text(a_element.text)

    # Employment Type
    employment_element = other_elements[3].find('span')
    if employment_element:
        span_element = employment_element.find('span')
        job_details["employment_type"] = clean_text(span_element.text)

    
    return job_details


async def scrape_job(job_url):
    options = webdriver.ChromeOptions()

    # options.add_argument('--headless') # Alternative to --headless=new
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)

    ua = UserAgent(os = "Windows")
    options.add_argument(f"user-agent={ua.random}")

    driver = None

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        driver.get(job_url)

        wait = WebDriverWait(driver, 30)

        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))



        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        return extract_job_details(soup, job_url)
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
        return None
    finally:
        try:
            if driver:
                driver.quit()
        except:
            print("Error closing driver")


if __name__ == "__main__":
    URL = "https://www.naukri.com/job-listings-service-desk-engineer-wipro-kolkata-pune-bengaluru-0-to-4-years-260225017321?src=drecomm_profile&sid=17422879425688541&xp=1&px=1"
    data = asyncio.run(scrape_job(URL))
    for key, value in data.items():
        print(f"{key}: {value}")