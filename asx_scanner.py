# asx_scanner.py - GitHub Actions optimized version
import requests
import pandas as pd
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from datetime import datetime, timedelta
import time
import re
import logging
import os
from typing import List, Dict, Optional
from dataclasses import dataclass
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Announcement:
    company_name: str
    company_code: str
    title: str
    content: str
    date: str
    time: str
    url: str
    sentiment: str = "neutral"
    key_points: List[str] = None

class ASXMiningScanner:
    def __init__(self):
        """Initialize the ASX Mining Scanner for GitHub Actions."""
        self.config = self.load_config_from_env()
        self.mining_companies = self.load_mining_companies()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def load_config_from_env(self) -> dict:
        """Load configuration from environment variables (GitHub Secrets)."""
        return {
            "email": {
                "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
                "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                "sender_email": os.getenv("SENDER_EMAIL"),
                "sender_password": os.getenv("SENDER_PASSWORD"),
                "recipient_email": os.getenv("RECIPIENT_EMAIL")
            },
            "scanning": {
                "lookback_days": 1,
                "keywords": ["drilling", "resource", "reserve", "production", "exploration", 
                           "acquisition", "merger", "feasibility", "offtake", "partnership",
                           "upgrade", "expansion", "mine", "operation", "project", "development"],
                "min_announcement_length": 30
            }
        }
    
    def load_mining_companies(self) -> List[Dict]:
        """Load comprehensive list of ASX mining companies."""
        companies = [
            # Major miners
            {"code": "BHP", "name": "BHP Group Limited", "sector": "Diversified Metals"},
            {"code": "RIO", "name": "Rio Tinto Limited", "sector": "Diversified Metals"},
            {"code": "FMG", "name": "Fortescue Metals Group Ltd", "sector": "Iron Ore"},
            {"code": "NCM", "name": "Newcrest Mining Limited", "sector": "Gold"},
            {"code": "EVN", "name": "Evolution Mining Limited", "sector": "Gold"},
            {"code": "NST", "name": "Northern Star Resources Ltd", "sector": "Gold"},
            {"code": "MIN", "name": "Mineral Resources Limited", "sector": "Diversified Metals"},
            {"code": "IGO", "name": "IGO Limited", "sector": "Nickel/Lithium"},
            
            # Gold miners
            {"code": "SBM", "name": "St Barbara Limited", "sector": "Gold"},
            {"code": "RSG", "name": "Resolute Mining Limited", "sector": "Gold"},
            {"code": "RRL", "name": "Regis Resources Limited", "sector": "Gold"},
            {"code": "SAR", "name": "Saracen Mineral Holdings Limited", "sector": "Gold"},
            {"code": "GOR", "name": "Gold Road Resources Limited", "sector": "Gold"},
            {"code": "DCN", "name": "Dacian Gold Limited", "sector": "Gold"},
            {"code": "KLA", "name": "Kirkland Lake Gold Ltd", "sector": "Gold"},
            {"code": "LRV", "name": "Larvotto Resources Limited", "sector": "Gold"},
            {"code": "TMR", "name": "Tempus Resources Ltd", "sector": "Gold"},
            {"code": "NVA", "name": "Nova Minerals Limited", "sector": "Gold"},
            
            # Lithium and battery metals
            {"code": "PLS", "name": "Pilbara Minerals Limited", "sector": "Lithium"},
            {"code": "ORE", "name": "Orocobre Limited", "sector": "Lithium"},
            {"code": "GXY", "name": "Galaxy Resources Limited", "sector": "Lithium"},
            {"code": "CXO", "name": "Core Lithium Ltd", "sector": "Lithium"},
            {"code": "LPD", "name": "Lepidico Ltd", "sector": "Lithium"},
            {"code": "ARI", "name": "Argosy Minerals Limited", "sector": "Lithium"},
            {"code": "ASN", "name": "Anson Resources Limited", "sector": "Lithium"},
            {"code": "LTR", "name": "Liontown Resources Limited", "sector": "Lithium"},
            
            # Uranium
            {"code": "BOE", "name": "Boss Energy Limited", "sector": "Uranium"},
            {"code": "PEN", "name": "Peninsula Energy Limited", "sector": "Uranium"},
            {"code": "BMN", "name": "Bannerman Energy Ltd", "sector": "Uranium"},
            {"code": "DYL", "name": "Deep Yellow Limited", "sector": "Uranium"},
            {"code": "LOT", "name": "Lotus Resources Limited", "sector": "Uranium"},
            
            # Copper
            {"code": "AZS", "name": "Azure Minerals Limited", "sector": "Copper"},
            {"code": "C6C", "name": "Copper Mountain Mining Corporation", "sector": "Copper"},
            {"code": "29M", "name": "29Metals Limited", "sector": "Copper"},
            {"code": "SFR", "name": "Sandfire Resources Limited", "sector": "Copper"},
            
            # Iron ore
            {"code": "GRR", "name": "Grange Resources Limited", "sector": "Iron Ore"},
            {"code": "AGO", "name": "Atlas Iron Limited", "sector": "Iron Ore"},
            {"code": "BCI", "name": "BC Iron Limited", "sector": "Iron Ore"},
            {"code": "FRI", "name": "Fortescue Future Industries", "sector": "Iron Ore"},
            
            # Other metals
            {"code": "MLS", "name": "Metals X Limited", "sector": "Tin"},
            {"code": "VMG", "name": "VanMag Limited", "sector": "Vanadium"},
            {"code": "FYI", "name": "FYI Resources Limited", "sector": "Alumina"},
            {"code": "SYR", "name": "Syrah Resources Limited", "sector": "Graphite"},
            {"code": "TNG", "name": "TNG Limited", "sector": "Titanium"},
            
            # Rare earths
            {"code": "LYC", "name": "Lynas Rare Earths Ltd", "sector": "Rare Earths"},
            {"code": "ARU", "name": "Arafura Resources Limited", "sector": "Rare Earths"},
            {"code": "IXR", "name": "Ionic Rare Earths Limited", "sector": "Rare Earths"},
            
            # Coal (if relevant)
            {"code": "WHC", "name": "Whitehaven Coal Limited", "sector": "Coal"},
            {"code": "NHC", "name": "New Hope Corporation Limited", "sector": "Coal"},
            
            # Energy/Oil & Gas
            {"code": "WDS", "name": "Woodside Energy Group Ltd", "sector": "Energy"},
            {"code": "STO", "name": "Santos Limited", "sector": "Energy"},
            {"code": "ORG", "name": "Origin Energy Limited", "sector": "Energy"},
            {"code": "EXR", "name": "Elixir Energy Limited", "sector": "Gas"}
        ]
        
        # Load additional companies from file if exists
        try:
            if os.path.exists("mining_companies.json"):
                with open("mining_companies.json", 'r') as f:
                    additional_companies = json.load(f)
                    companies.extend(additional_companies)
        except Exception as e:
            logger.warning(f"Could not load additional companies: {e}")
        
        return companies
    
    def get_asx_announcements(self, date: str = None) -> List[Dict]:
        """Scrape ASX announcements using multiple sources."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        announcements = []
        
        # Method 1: Try Market Index
        announcements.extend(self.scrape_market_index())
        
        # Method 2: Try ASX-specific financial sites
        announcements.extend(self.scrape_simply_wall_st())
        
        # Method 3: Try CommSec or other sources
        announcements.extend(self.scrape_commsec_style())
        
        # Remove duplicates based on company code and title
        unique_announcements = []
        seen = set()
        for ann in announcements:
            key = f"{ann.get('company_code', '')}-{ann.get('title', '')}"
            if key not in seen:
                seen.add(key)
                unique_announcements.append(ann)
        
        return unique_announcements
    
    def scrape_market_index(self) -> List[Dict]:
        """Scrape from Market Index website."""
        announcements = []
        try:
            url = "https://www.marketindex.com.au/asx/announcements"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for various table structures
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header
                    try:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 3:
                            time_text = cells[0].get_text(strip=True)
                            company_text = cells[1].get_text(strip=True)
                            title_text = cells[2].get_text(strip=True)
                            
                            # Extract company code
                            company_match = re.search(r'\b([A-Z]{2,4})\b', company_text)
                            if company_match:
                                company_code = company_match.group(1)
                                if self.is_mining_company(company_code):
                                    company_name = re.sub(r'\([A-Z]{2,4}\)', '', company_text).strip()
                                    
                                    announcements.append({
                                        'time': time_text,
                                        'company_code': company_code,
                                        'company_name': company_name,
                                        'title': title_text,
                                        'date': datetime.now().strftime("%Y-%m-%d"),
                                        'url': url,
                                        'content': title_text
                                    })
                    except Exception as e:
                        continue
                        
        except Exception as e:
            logger.error(f"Error scraping Market Index: {e}")
        
        return announcements
    
    def scrape_simply_wall_st(self) -> List[Dict]:
        """Scrape from Simply Wall St or similar financial sites."""
        announcements = []
        try:
            # This would be implemented with specific site structure
            # For now, return empty list
            pass
        except Exception as e:
            logger.error(f"Error scraping Simply Wall St: {e}")
        
        return announcements
    
    def scrape_commsec_style(self) -> List[Dict]:
        """Scrape from CommSec-style announcement feeds."""
        announcements = []
        try:
            # Alternative sources could be added here
            # For example, RSS feeds or other financial news sites
            pass
        except Exception as e:
            logger.error(f"Error scraping CommSec style: {e}")
        
        return announcements
    
    def is_mining_company(self, company_code: str) -> bool:
        """Check if a company code belongs to a mining company."""
        return any(company['code'] == company_code for company in self.mining_companies)
    
    def get_company_info(self, company_code: str) -> Optional[Dict]:
        """Get company information by code."""
        for company in self.mining_companies:
            if company['code'] == company_code:
                return company
        return None
    
    def analyze_announcement(self, announcement: Dict) -> Announcement:
        """Analyze and categorize an announcement."""
        title = announcement.get('title', '')
        content = announcement.get('content', title)
        
        # Enhanced sentiment analysis
        positive_keywords = [
            'increase', 'growth', 'strong', 'successful', 'positive', 'upgrade', 
            'expansion', 'discovery', 'high-grade', 'significant', 'excellent',
            'breakthrough', 'achievement', 'record', 'boost', 'progress'
        ]
        negative_keywords = [
            'decrease', 'decline', 'loss', 'suspension', 'delay', 'downgrade', 
            'closure', 'reduction', 'cut', 'lower', 'disappointing', 'concern',
            'issue', 'problem', 'halt', 'stop'
        ]
        
        sentiment = "neutral"
        title_lower = title.lower()
        
        positive_score = sum(1 for keyword in positive_keywords if keyword in title_lower)
        negative_score = sum(1 for keyword in negative_keywords if keyword in title_lower)
        
        if positive_score > negative_score:
            sentiment = "positive"
        elif negative_score > positive_score:
            sentiment = "negative"
        
        # Extract key points
        key_points = []
        for keyword in self.config['scanning']['keywords']:
            if keyword.lower() in title_lower:
                key_points.append(f"Related to {keyword}")
        
        return Announcement(
            company_name=announcement.get('company_name', ''),
            company_code=announcement.get('company_code', ''),
            title=title,
            content=content,
            date=announcement.get('date', ''),
            time=announcement.get('time', ''),
            url=announcement.get('url', ''),
            sentiment=sentiment,
            key_points=key_points
        )
    
    def format_announcement_summary(self, announcement: Announcement) -> str:
        """Format announcement in the requested style."""
        company_info = self.get_company_info(announcement.company_code)
        
        # Enhanced formatting to match your examples more closely
        title = announcement.title
        
        # Look for project/location names in titles
        project_match = re.search(r'\b(at|from|in)\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|,|\()', title)
        location_match = re.search(r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(?:Project|Mine|Deposit|Operation)', title)
        
        summary = f"• **{announcement.company_name}** "
        
        # Add contextual information based on title content
        if 'production' in title.lower():
            summary += "reported production "
        elif 'drilling' in title.lower():
            summary += "announced drilling "
        elif 'resource' in title.lower():
            summary += "updated resource "
        elif 'approval' in title.lower():
            summary += "received approval "
        elif 'acquisition' in title.lower():
            summary += "announced acquisition "
        else:
            summary += "announced "
        
        # Add project/location if found
        if project_match:
            project_name = project_match.group(2).strip()
            summary += f"at **{project_name}** "
        elif location_match:
            location_name = location_match.group(1).strip()
            summary += f"for **{location_name}** "
        
        # Add key metrics or numbers if found
        numbers = re.findall(r'(\d+(?:\.\d+)?(?:Mlb|klb|Mt|kt|oz|%|million|billion))', title)
        if numbers:
            summary += f"with {numbers[0]} "
        
        # Add main content
        summary += f"- {title}"
        
        # Add company code
        summary += f" ({announcement.company_code})"
        
        return summary
    
    def generate_daily_report(self, announcements: List[Announcement]) -> str:
        """Generate the daily email report."""
        if not announcements:
            return f"""
# ASX Mining Daily Report - {datetime.now().strftime('%B %d, %Y')}

## Summary
No significant mining announcements found for today.

The scanner checked {len(self.mining_companies)} mining companies but found no new announcements meeting the criteria.

---
*Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC*
*Monitoring {len(self.mining_companies)} ASX mining companies*
"""
        
        # Group by sentiment
        positive_announcements = [a for a in announcements if a.sentiment == "positive"]
        neutral_announcements = [a for a in announcements if a.sentiment == "neutral"]
        negative_announcements = [a for a in announcements if a.sentiment == "negative"]
        
        report = f"""
# ASX Mining Daily Report - {datetime.now().strftime('%B %d, %Y')}

## Summary
Found {len(announcements)} significant announcements from mining companies today.

## Key Announcements

"""
        
        # Add positive news first
        if positive_announcements:
            report += "### 📈 Positive Developments\n"
            for announcement in positive_announcements:
                report += self.format_announcement_summary(announcement) + "\n"
            report += "\n"
        
        # Add neutral news
        if neutral_announcements:
            report += "### 📊 General Updates\n"
            for announcement in neutral_announcements:
                report += self.format_announcement_summary(announcement) + "\n"
            report += "\n"
        
        # Add negative news
        if negative_announcements:
            report += "### 📉 Challenges/Concerns\n"
            for announcement in negative_announcements:
                report += self.format_announcement_summary(announcement) + "\n"
            report += "\n"
        
        # Company breakdown
        companies = {}
        for announcement in announcements:
            if announcement.company_code not in companies:
                companies[announcement.company_code] = []
            companies[announcement.company_code].append(announcement)
        
        report += "## Company Breakdown\n"
        for company_code, company_announcements in sorted(companies.items()):
            company_info = self.get_company_info(company_code)
            company_name = company_info['name'] if company_info else company_announcements[0].company_name
            sector = company_info['sector'] if company_info else "Mining"
            report += f"**{company_name} ({company_code})** - {sector}: {len(company_announcements)} announcement(s)\n"
        
        report += f"""

## Sector Summary
"""
        
        # Sector breakdown
        sectors = {}
        for announcement in announcements:
            company_info = self.get_company_info(announcement.company_code)
            sector = company_info['sector'] if company_info else "Other"
            if sector not in sectors:
                sectors[sector] = 0
            sectors[sector] += 1
        
        for sector, count in sorted(sectors.items(), key=lambda x: x[1], reverse=True):
            report += f"- {sector}: {count} announcement(s)\n"
        
        report += f"""

---
*Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC*
*Monitoring {len(self.mining_companies)} ASX mining companies*
*Next report: Tomorrow at 8:00 AM AEST*
"""
        
        return report
    
    def send_email_report(self, report: str):
        """Send the daily report via email."""
        try:
            if not all([
                self.config['email']['sender_email'],
                self.config['email']['sender_password'],
                self.config['email']['recipient_email']
            ]):
                logger.error("Email configuration incomplete")
                return
            
            msg = MimeMultipart()
            msg['From'] = self.config['email']['sender_email']
            msg['To'] = self.config['email']['recipient_email']
            msg['Subject'] = f"ASX Mining Daily Report - {datetime.now().strftime('%Y-%m-%d')}"
            
            msg.attach(MimeText(report, 'plain'))
            
            server = smtplib.SMTP(self.config['email']['smtp_server'], self.config['email']['smtp_port'])
            server.starttls()
            server.login(self.config['email']['sender_email'], self.config['email']['sender_password'])
            text = msg.as_string()
            server.sendmail(
                self.config['email']['sender_email'], 
                self.config['email']['recipient_email'], 
                text
            )
            server.quit()
            
            logger.info(f"Email report sent successfully to {self.config['email']['recipient_email']}")
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            raise
    
    def run_daily_scan(self):
        """Run the daily scanning process."""
        logger.info("Starting daily ASX mining scan...")
        
        try:
            # Get announcements
            raw_announcements = self.get_asx_announcements()
            logger.info(f"Found {len(raw_announcements)} raw announcements")
            
            # Filter and analyze announcements
            analyzed_announcements = []
            for raw_announcement in raw_announcements:
                try:
                    analyzed = self.analyze_announcement(raw_announcement)
                    if len(analyzed.title) >= self.config['scanning']['min_announcement_length']:
                        analyzed_announcements.append(analyzed)
                except Exception as e:
                    logger.error(f"Error analyzing announcement: {e}")
                    continue
            
            logger.info(f"Processed {len(analyzed_announcements)} significant announcements")
            
            # Generate report
            report = self.generate_daily_report(analyzed_announcements)
            
            # Save report to file
            report_filename = f"reports/mining_report_{datetime.now().strftime('%Y%m%d')}.md"
            os.makedirs("reports", exist_ok=True)
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Report saved to {report_filename}")
            
            # Print report to GitHub Actions log
            print("=" * 80)
            print(report)
            print("=" * 80)
            
            # Send email
            self.send_email_report(report)
            
            logger.info("Daily scan completed successfully")
            
        except Exception as e:
            logger.error(f"Error in daily scan: {e}")
            # Send error notification
            error_report = f"""
# ASX Mining Scanner - Error Report

An error occurred during today's scan: {str(e)}

Please check the GitHub Actions logs for more details.

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""
            try:
                self.send_email_report(error_report)
            except:
                logger.error("Could not send error notification email")
            raise

def main():
    """Main function for GitHub Actions."""
    logger.info("ASX Mining Scanner starting...")
    scanner = ASXMiningScanner()
    scanner.run_daily_scan()
    logger.info("ASX Mining Scanner completed.")

if __name__ == "__main__":
    main()
