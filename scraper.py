import requests
from bs4 import BeautifulSoup
import os
import time
import re
import config
from urllib.parse import urljoin, urlparse
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import logging
from datetime import datetime
import json

class WebScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc.replace('www.', '')
        self.base_dir = os.path.join('data', self.sanitize_filename(self.domain))
        
        # إنشاء المجلدات الأساسية
        self.images_dir = os.path.join(self.base_dir, 'images')
        self.data_dir = os.path.join(self.base_dir, 'data')
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # إعداد التسجيل
        log_file = os.path.join(self.base_dir, 'scraping.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # إعداد Selenium
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
        # إعداد جلسة الطلبات
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        })

    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.quit()

    def save_metadata(self, data):
        """Save metadata to JSON file"""
        metadata = {
            'url': self.base_url,
            'domain': self.domain,
            'scrape_date': datetime.now().isoformat(),
            'stats': {
                'images_count': len(data.get('images', [])),
                'headers_count': len(data.get('headers', [])),
                'paragraphs_count': len(data.get('paragraphs', [])),
                'links_count': len(data.get('links', [])),
            },
            'data': data
        }
        
        metadata_file = os.path.join(self.data_dir, 'metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f'Metadata saved to: {metadata_file}')

    def save_text_content(self, data):
        """Save text content to separate files"""
        # Save headers
        headers_file = os.path.join(self.data_dir, 'headers.txt')
        with open(headers_file, 'w', encoding='utf-8') as f:
            for header in data.get('headers', []):
                if header and not header.isspace():
                    f.write(f'{header}\n')
        
        # Save paragraphs
        paragraphs_file = os.path.join(self.data_dir, 'paragraphs.txt')
        with open(paragraphs_file, 'w', encoding='utf-8') as f:
            for para in data.get('paragraphs', []):
                if para and not para.isspace():
                    f.write(f'{para}\n\n')
        
        # Save links
        links_file = os.path.join(self.data_dir, 'links.txt')
        with open(links_file, 'w', encoding='utf-8') as f:
            for link in data.get('links', []):
                if link and not link.isspace():
                    f.write(f'{link}\n')

    def download_images(self):
        """Download and save images to the designated folder"""
        self.logger.info('Loading page...')
        try:
            self.driver.set_page_load_timeout(30)
            self.driver.get(self.base_url)
            self.wait_for_page_load()
            self.scroll_page()
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            image_urls = self.get_image_urls(soup)
            
            if not image_urls:
                self.logger.warning("No images found on the page")
                return []
                
            self.logger.info(f'Found {len(image_urls)} images')
            downloaded_images = []
            
            for img_url in image_urls:
                if not img_url or img_url.startswith('data:'):
                    continue
                    
                if not img_url.startswith(('http://', 'https://')):
                    img_url = urljoin(self.base_url, img_url)

                try:
                    response = self.session.get(img_url, timeout=10, stream=True)
                    response.raise_for_status()
                    
                    content_type = response.headers.get('content-type', '')
                    if not content_type.startswith('image/'):
                        self.logger.warning(f'Skipping non-image URL: {img_url} (type: {content_type})')
                        continue
                    
                    filename = self.sanitize_filename(os.path.basename(urlparse(img_url).path))
                    if not filename or filename == '.':
                        filename = f'image_{len(downloaded_images) + 1}{os.path.splitext(filename)[1] or ".jpg"}'
                        
                    full_path = os.path.join(self.images_dir, filename)
                    
                    with open(full_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    
                    image_info = {
                        'filename': filename,
                        'original_url': img_url,
                        'content_type': content_type,
                        'size': os.path.getsize(full_path)
                    }
                    downloaded_images.append(image_info)
                    
                    self.logger.info(f'Saved: {filename}')
                    time.sleep(0.5)
                    
                except requests.exceptions.RequestException as e:
                    self.logger.error(f'Failed to download {img_url}: {str(e)}')
                except Exception as e:
                    self.logger.error(f'Unexpected error downloading {img_url}: {str(e)}')
            
            self.logger.info(f'Successfully downloaded {len(downloaded_images)} images')
            return downloaded_images
                    
        except Exception as e:
            self.logger.error(f'Error processing page: {str(e)}')
            return []

    def scrape(self):
        """Extract all data from the website"""
        try:
            # Download images
            images = self.download_images()
            
            # Extract text content
            self.driver.get(self.base_url)
            self.wait_for_page_load()
            self.scroll_page()
            
            # Wait for dynamic content
            time.sleep(2)
            
            # Get page source after JavaScript execution
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract text content
            text_content = self.extract_text_content(soup)
            
            data = {
                'headers': text_content['headers'],
                'paragraphs': text_content['paragraphs'],
                'links': text_content['links'],
                'images': images
            }
            
            # Save data
            self.save_metadata(data)
            self.save_text_content(data)
            
            return data
            
        except Exception as e:
            self.logger.error(f'Error extracting data: {str(e)}')
            return None

    def wait_for_page_load(self):
        """Wait for the page to load completely"""
        try:
            self.wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
            time.sleep(3)
        except Exception as e:
            self.logger.warning(f"Error waiting for page load: {str(e)}")

    def scroll_page(self):
        """Scroll the page to load dynamic content"""
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
        except Exception as e:
            self.logger.warning(f"Error scrolling page: {str(e)}")

    def extract_text_content(self, soup):
        """Extract text content from the page with better handling of dynamic content"""
        # Extract headers
        headers = []
        for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            # Remove any script or style elements
            for element in h.find_all(['script', 'style']):
                element.decompose()
            text = h.get_text(strip=True, separator=' ')
            if text and not text.isspace():
                headers.append(text)

        # Extract paragraphs from various content containers
        paragraphs = []
        content_selectors = [
            'p', 'article', 'section', '.content', '.text',
            '[class*="content"]', '[class*="text"]', '[class*="body"]',
            'div > p', 'main p', 'article p'
        ]
        
        for selector in content_selectors:
            for element in soup.select(selector):
                # Skip if parent is already processed
                if any(p in paragraphs for p in element.parents):
                    continue
                    
                # Remove any script, style, or nav elements
                for unwanted in element.find_all(['script', 'style', 'nav']):
                    unwanted.decompose()
                    
                text = element.get_text(strip=True, separator=' ')
                if text and not text.isspace() and len(text) > 20:  # Minimum length to filter noise
                    if text not in paragraphs:  # Avoid duplicates
                        paragraphs.append(text)

        # Extract links
        links = []
        for a in soup.find_all('a', href=True):
            href = a.get('href')
            if href and not href.startswith('#') and href != '/':
                if not href.startswith(('http://', 'https://')):
                    href = urljoin(self.base_url, href)
                if href not in links:  # Avoid duplicates
                    links.append(href)

        return {
            'headers': headers,
            'paragraphs': paragraphs,
            'links': links
        }

    @staticmethod
    def sanitize_filename(name):
        # Get file extension if exists
        name, ext = os.path.splitext(name)
        # Remove invalid characters
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        # Ensure the filename is not empty
        if not name:
            name = 'image'
        return (name + ext).strip()

    def get_image_urls(self, soup):
        image_urls = set()
        
        try:
            # Wait for images to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "img")))
            
            # 1. Find all image elements
            selectors = [
                'img[src]', 'img[data-src]', 'img[data-original]',
                'div[style*="background-image"]', 'div[data-bg]',
                'picture source[srcset]'
            ]
            
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    # Check multiple attributes
                    for attr in ['src', 'data-src', 'data-original', 'srcset', 'data-bg']:
                        value = element.get_attribute(attr)
                        if value:
                            if ',' in value:  # Handle srcset
                                urls = value.split(',')
                                for url in urls:
                                    image_url = url.strip().split(' ')[0]
                                    image_urls.add(image_url)
                            else:
                                image_urls.add(value)
                    
                    # Check background image
                    style = element.get_attribute('style')
                    if style and 'background-image' in style:
                        urls = re.findall(r'url\(["\']?(.*?)["\']?\)', style)
                        image_urls.update(urls)

            # 2. Execute JavaScript to find hidden images
            js_images = self.driver.execute_script("""
                var images = [];
                var elements = document.getElementsByTagName('*');
                for (var i = 0; i < elements.length; i++) {
                    var style = window.getComputedStyle(elements[i], null);
                    var bg = style.backgroundImage;
                    if (bg && bg !== 'none') images.push(bg);
                }
                return images;
            """)
            
            for img in js_images:
                urls = re.findall(r'url\(["\']?(.*?)["\']?\)', img)
                image_urls.update(urls)

        except Exception as e:
            self.logger.error(f"Error extracting images: {str(e)}")

        return image_urls
