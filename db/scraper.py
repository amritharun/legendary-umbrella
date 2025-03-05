import requests
import polars as pl
import time
import os
from datetime import datetime
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from requests_ratelimiter import LimiterSession
import requests_cache


class SECNPortScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'amrith321@gmail.com',
        }
        self.session = requests_cache.CachedSession('legendary_umbrella', expire_after=3600)
        self.limited_session = LimiterSession(session=self.session, per_second=8)
        
    def get_filing_metadata(self, cik, filing_type="NPORT-P", count=10):
        """Get metadata for N-PORT filings for a specific CIK"""
        # Format CIK with leading zeros to 10 digits
        cik = cik.lstrip('0')
        cik_padded = cik.zfill(10)
        
        url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        
        print(f"Requesting metadata from: {url}")
        response = self.limited_session.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"Error fetching data: {response.status_code}")
            return []
        
        data = response.json()
        filings = []
        filing_dict = data.get('filings', []).get('recent', {})
        if not filing_dict:
            print("No filings found")
            return []
        for (accension_number, filing_date, c) in zip(filing_dict.get("accessionNumber", []), filing_dict.get("filingDate", []), range(count)):
            if c == count:
                break
            filings.append({
                "accessionNumber": accension_number,
                "filingDate": filing_date
            })
                    
        return filings
    
    def get_filing_contents(self, accession_number, cik):
        """Get XML content of a specific N-PORT filing"""
        # Format accession number for URL
        acc_no_dash = accession_number.replace('-', '')
        cik = cik.lstrip('0')
        
        # Construct URL to the index page
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dash}/{accession_number}-index.html"
        
        print(f"Requesting filing index: {url}")
        response = self.limited_session.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"Error fetching filing index: {response.status_code}")
            return None
        
        # Parse HTML to find the XML document link
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for XML file (primary document)
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 3:
                if 'xml' in cells[2].text.lower() and ('primary_doc' in row.text.lower() or 'nport' in cells[2].text.lower()):
                    xml_filename = cells[2].text.strip()
                    xml_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dash}/{xml_filename}"
                    
                    
                    print(f"Downloading XML: {xml_url}")
                    xml_response = self.limited_session.get(xml_url, headers=self.headers)
                    
                    if xml_response.status_code == 200:
                        return xml_response.text
                    else:
                        print(f"Error downloading XML: {xml_response.status_code}")
        
        return None
    
    def extract_targeted_data(self, xml_content):
        """Extract only CUSIP, name/title, balance, and value from N-PORT XML"""
        if not xml_content:
            return []
        
        # Parse XML
        try:
            root = ET.fromstring(xml_content)
            
            # Common namespaces used in N-PORT filings
            namespaces = {
                'n1': 'http://www.sec.gov/edgar/nport',
                'n2': 'http://www.sec.gov/edgar/common',
                'n3': 'http://www.sec.gov/edgar/document/nport/primary',
                'n4': 'http://www.sec.gov/edgar/documents/nport'
            }
            
            # Find all investment elements (holdings)
            holdings = []
            investment_found = False
            
            # Try different namespace patterns as SEC sometimes changes them
            for ns_prefix, ns_uri in namespaces.items():
                # Look for investment elements
                investments = root.findall(f'.//{{{ns_uri}}}invstOrSec')
                
                if not investments:
                    # Try alternative element names
                    investments = root.findall(f'.//{{{ns_uri}}}invstOrSecurity')
                
                if not investments:
                    # Try with portfolioInvestments parent
                    portfolios = root.findall(f'.//{{{ns_uri}}}portfolioInvestments')
                    if portfolios:
                        for portfolio in portfolios:
                            invests = portfolio.findall(f'.//{{{ns_uri}}}invstOrSec')
                            if invests:
                                investments = invests
                                break
                
                if investments:
                    investment_found = True
                    for inv in investments:
                        holding = {}

                        # Extract name/title
                        name_elem = inv.find(f'.//{{{ns_uri}}}name')
                        if name_elem is not None and name_elem.text:
                            holding['company'] = name_elem.text
                        else:
                            # Try title as an alternative
                            title_elem = inv.find(f'.//{{{ns_uri}}}title')
                            if title_elem is not None and title_elem.text:
                                holding['company'] = title_elem.text
                            else:
                                holding['company'] = "Unknown"
                        
                        # Extract CUSIP
                        cusip_elem = None
                        # Look for CUSIP in different possible locations
                        id_elem = inv.find(f'.//{{{ns_uri}}}cusip')
                        if id_elem is not None and id_elem.text:
                            holding['cusip'] = id_elem.text
                        else:
                            holding['cusip'] = "N/A"
                        
                        # Extract balance
                        balance_elem = inv.find(f'.//{{{ns_uri}}}balance')
                        if balance_elem is not None and balance_elem.text:
                            holding['balance'] = float(balance_elem.text)
                        else:
                            # Try alternative names
                            balance_elem = inv.find(f'.//{{{ns_uri}}}units')
                            if balance_elem is not None and balance_elem.text:
                                holding['balance'] = float(balance_elem.text)
                            else:
                                balance_elem = inv.find(f'.//{{{ns_uri}}}quantity')
                                if balance_elem is not None and balance_elem.text:
                                    holding['balance'] = float(balance_elem.text)
                                else:
                                    holding['balance'] = "N/A"
                        
                        # Extract value
                        value_elem = inv.find(f'.//{{{ns_uri}}}valUSD')
                        if value_elem is not None and value_elem.text:
                            holding['value'] = value_elem.text
                        else:
                            # Try alternative name
                            value_elem = inv.find(f'.//{{{ns_uri}}}value')
                            if value_elem is not None and value_elem.text:
                                holding['value'] = value_elem.text
                            else:
                                value_elem = inv.find(f'.//{{{ns_uri}}}value')
                                if value_elem is not None and value_elem.text:
                                    holding['value'] = value_elem.text
                                else:
                                    holding['value'] = "N/A"
                        
                        holdings.append(holding)
                    
                    # Break once we've found and processed investments
                    break
            
            # If we couldn't find investments with the standard approach, try a more generic approach
            if not investment_found:
                print("Using fallback method to find holdings...")
                # Look for any elements that might contain "name" and "cusip"
                for elem in root.iter():
                    if elem.tag.endswith('}name') or elem.tag.endswith('}title'):
                        holding = {'name': elem.text if elem.text else "Unknown"}
                        
                        # Try to find sibling or related elements for other fields
                        parent = elem.getparent() if hasattr(elem, 'getparent') else None
                        if parent is not None:
                            # Look through siblings or parent's children
                            for child in parent:
                                tag = child.tag.split('}')[-1].lower()
                                
                                if 'cusip' in tag and child.text:
                                    holding['cusip'] = child.text
                                elif any(x in tag for x in ['balance', 'units', 'quantity']) and child.text:
                                    holding['balance'] = child.text
                                elif any(x in tag for x in ['value', 'amount', 'amt']) and child.text:
                                    holding['value'] = child.text
                            
                            # Add default values for missing fields
                            holding.setdefault('cusip', "N/A")
                            holding.setdefault('balance', "N/A")
                            holding.setdefault('value', "N/A")
                            
                            holdings.append(holding)
            
            return holdings
            
        except ET.ParseError as e:
            print(f"Error parsing XML: {e}")
            return []
    
    def scrape_targeted_nport_data(self, cik, max_filings=1):
        """Scrape targeted data (CUSIP, name, balance, value) from N-PORT filings"""
        print(f"Scraping N-PORT data for CIK {cik}")
        # Get filing metadata
        filings = self.get_filing_metadata(cik, count=max_filings)
        
        if not filings:
            print(f"No N-PORT filings found for CIK {cik}")
            return None
            
        print(f"Found {len(filings)} N-PORT filings")
        
        # Process each filing
        all_holdings = []
        
        for filing in filings:
            print(f"\nProcessing filing from {filing['filingDate']} (Accession: {filing['accessionNumber']})")
            
            # Get filing contents
            xml_content = self.get_filing_contents(filing['accessionNumber'], cik)
            
            if xml_content:
                # Extract targeted data
                holdings = self.extract_targeted_data(xml_content)
                
                if holdings:
                    # Add filing metadata to each holding
                    for holding in holdings:
                        holding['date'] = filing['filingDate']
                        holding['cik'] = cik
                        holding['accession_number'] = filing['accessionNumber']
                        all_holdings.append(holding)
                    
                    print(f"Successfully extracted {len(holdings)} holdings")
                else:
                    print(f"No holdings found in this filing")
            else:
                print(f"Failed to retrieve filing contents")
                
        return all_holdings
    
# Example usage
def main():
    # Initialize scraper
    scraper = SECNPortScraper()
    
    # Input CIK number (example: Vanguard Total Stock Market Index Fund)
    cik = "0000884394"# Replace with your target CIK
    
    # Scrape the data
    holdings = scraper.scrape_targeted_nport_data(cik, max_filings=1)
    df = pl.DataFrame(holdings)
    print(df)
    
    

if __name__ == "__main__":
    main()