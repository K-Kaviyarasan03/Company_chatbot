# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import time 

class ActionScrapeCompany(Action):
    def name(self) -> Text:
        return "action_scrape_company"

    def find_company_website(self, company_name: str) -> str:
        """
        Try to find company website using direct URL format and common variations
        """
        # Clean company name
        company_name = company_name.lower().strip()
        company_name = re.sub(r'[^a-z0-9]', '', company_name)
        
        # List of common domain variations to try
        urls_to_try = [
            f"https://{company_name}.com",
            f"https://www.{company_name}.com",
            f"https://{company_name}.co",
            f"https://www.{company_name}.co",
            f"https://{company_name}.org",
            f"https://www.{company_name}.org",
            f"https://{company_name}.net",
            f"https://www.{company_name}.net",
            f"https://www.{company_name}.com/in/",
            f"https://www.{company_name}.co.in/",
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Try each URL variation
        for url in urls_to_try:
            try:
                response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    return url
            except Exception:
                continue
        
        return None

    def extract_company_info(self, url: str) -> Dict:
        """Extract relevant information from the company website."""
        try:
            headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...'
}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract useful information
            info = {
                'title': soup.title.string if soup.title else "No title found",
                'description': "",
                'contact_info': [],
                'social_links': []
            }
            
            # Try to find meta description
            meta_desc = soup.find('meta', {'name': ['description', 'Description']})
            if meta_desc:
                info['description'] = meta_desc.get('content', '')
            
            # Look for contact information
            contact_patterns = [
                r'[\w\.-]+@[\w\.-]+\.\w+',  # Email
                r'\+\d{1,3}[-.\s]?\d{1,14}',  # Phone
                r'contact|about|about-us'  # Contact/About pages
            ]
            
            text_content = soup.get_text()
            for pattern in contact_patterns:
                matches = re.finditer(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    if match.group() not in info['contact_info']:
                        info['contact_info'].append(match.group())
            
            # Find social media links
            social_patterns = ['facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com']
            for link in soup.find_all('a', href=True):
                href = link['href']
                if any(pattern in href.lower() for pattern in social_patterns):
                    info['social_links'].append(href)
            
            return info
        except Exception as e:
            return {'error': str(e)}

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get company name from user's message
        company_name = next(tracker.get_latest_entity_values("company_name"), None)
        
        if not company_name:
            dispatcher.utter_message(text="I couldn't find a company name. Please provide a valid company name.")
            return []

        # Find company website
        website_url = self.find_company_website(company_name)
        
        if not website_url:
            dispatcher.utter_message(text=f"Sorry, I couldn't find a working website for {company_name}. The company might be using a different domain name format.")
            return []
        
        # Extract information from website
        info = self.extract_company_info(website_url)
        
        if 'error' in info:
            dispatcher.utter_message(text=f"Found the website but encountered an error while analyzing it: {info['error']}")
            return []
        
        # Format and send response
        response_text = f"Here's what I found about {company_name}:\n\n"
        response_text += f"Website: {website_url}\n\n"
        
        if info['title']:
            response_text += f"Title: {info['title']}\n\n"
            
        if info['description']:
            response_text += f"Description: {info['description']}\n\n"
            
        if info['contact_info']:
            response_text += "Contact Information:\n"
            for contact in info['contact_info'][:3]:  # Limit to first 3 items
                response_text += f"- {contact}\n"
            response_text += "\n"
            
        if info['social_links']:
            response_text += "Social Media:\n"
            for link in info['social_links'][:3]:  # Limit to first 3 links
                response_text += f"- {link}\n"
        
        dispatcher.utter_message(text=response_text)
        
        return []