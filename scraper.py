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
        self.domain = urlparse(base_url).netloc
        
        # Create directory for website
        self.base_dir = os.path.join('data', self.domain)
        
        # Create main directories
        self.images_dir = os.path.join(self.base_dir, 'images')
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.css_dir = os.path.join(self.base_dir, 'css')
        self.js_dir = os.path.join(self.base_dir, 'js')
        
        # Create directories
        for directory in [self.images_dir, self.data_dir, self.css_dir, self.js_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Set up logging
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
        
        # Set up Selenium
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
        
        # Set up requests session
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

    def process_css(self, css_url):
        """Process and download CSS files"""
        try:
            if not css_url.startswith(('http://', 'https://')):
                css_url = urljoin(self.base_url, css_url)
            
            response = self.session.get(css_url)
            response.raise_for_status()
            css_content = response.text
            
            # Update image paths in CSS
            css_content = self.update_css_paths(css_content, css_url)
            
            # Save CSS file
            css_filename = self.sanitize_filename(os.path.basename(urlparse(css_url).path))
            if not css_filename.endswith('.css'):
                css_filename += '.css'
            
            css_path = os.path.join(self.css_dir, css_filename)
            with open(css_path, 'w', encoding='utf-8') as f:
                f.write(css_content)
            
            self.logger.info(f'Saved CSS file: {css_filename}')
            return css_filename
            
        except Exception as e:
            self.logger.error(f'Error processing CSS {css_url}: {str(e)}')
            return None

    def update_css_paths(self, css_content, css_url):
        """Update image paths in CSS"""
        urls = re.findall(r'url\(["\']?(.*?)["\']?\)', css_content)
        for url in urls:
            if url.startswith('data:'):
                continue
                
            absolute_url = urljoin(css_url, url)
            filename = self.sanitize_filename(os.path.basename(urlparse(absolute_url).path))
            
            # Download image
            if any(absolute_url.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg']):
                img_path = os.path.join(self.images_dir, filename)
                self.download_file(absolute_url, img_path)
                css_content = css_content.replace(url, f'../images/{filename}')
        
        return css_content

    def process_javascript(self, js_url):
        """Process and download JavaScript files"""
        try:
            if not js_url.startswith(('http://', 'https://')):
                js_url = urljoin(self.base_url, js_url)
            
            response = self.session.get(js_url)
            response.raise_for_status()
            
            js_filename = self.sanitize_filename(os.path.basename(urlparse(js_url).path))
            if not js_filename.endswith('.js'):
                js_filename += '.js'
            
            js_path = os.path.join(self.js_dir, js_filename)
            with open(js_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            self.logger.info(f'Saved JavaScript file: {js_filename}')
            return js_filename
            
        except Exception as e:
            self.logger.error(f'Error processing JavaScript {js_url}: {str(e)}')
            return None

    def download_file(self, url, local_path):
        """Download a file and save it locally"""
        try:
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.logger.info(f'Downloaded: {os.path.basename(local_path)}')
            return True
            
        except Exception as e:
            self.logger.error(f'Error downloading {url}: {str(e)}')
            return False

    def combine_css_files(self, css_files):
        """Combine all CSS files into one file"""
        combined_css = []
        for css_file in css_files:
            file_path = os.path.join(self.css_dir, css_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                combined_css.append(f'/* {css_file} */\n{content}\n')
        
        # Save combined CSS
        combined_file = os.path.join(self.base_dir, 'styles.css')
        with open(combined_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(combined_css))
        
        self.logger.info('Combined all CSS files into styles.css')
        return 'styles.css'

    def combine_js_files(self, js_files):
        """Combine all JavaScript files into one file"""
        combined_js = []
        for js_file in js_files:
            file_path = os.path.join(self.js_dir, js_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                combined_js.append(f'// {js_file}\n{content}\n')
        
        # Save combined JavaScript
        combined_file = os.path.join(self.base_dir, 'script.js')
        with open(combined_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(combined_js))
        
        self.logger.info('Combined all JavaScript files into script.js')
        return 'script.js'

    def clone_website(self):
        """Clone the entire website with all files"""
        try:
            self.logger.info(f'Starting website clone: {self.base_url}')
            
            # Load page
            self.driver.get(self.base_url)
            self.wait_for_page_load()
            self.scroll_page()
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Process CSS files
            css_files = []
            for link in soup.find_all('link', rel='stylesheet'):
                css_url = link.get('href')
                if css_url:
                    css_filename = self.process_css(css_url)
                    if css_filename:
                        css_files.append(css_filename)
            
            # Process JavaScript files
            js_files = []
            for script in soup.find_all('script', src=True):
                js_url = script['src']
                js_filename = self.process_javascript(js_url)
                if js_filename:
                    js_files.append(js_filename)
            
            # Process images
            images = self.download_images()
            for img in soup.find_all('img'):
                src = img.get('src')
                if src in images:
                    img['src'] = f'images/{os.path.basename(images[src])}'
            
            # Combine CSS files
            combined_css = self.combine_css_files(css_files)
            
            # Combine JavaScript files
            combined_js = self.combine_js_files(js_files)
            
            # Update HTML to use combined files
            for link in soup.find_all('link', rel='stylesheet'):
                link.decompose()
            css_link = soup.new_tag('link', rel='stylesheet', href=combined_css)
            soup.head.append(css_link)
            
            for script in soup.find_all('script', src=True):
                script.decompose()
            js_script = soup.new_tag('script', src=combined_js)
            soup.body.append(js_script)
            
            # Save final HTML
            html_path = os.path.join(self.base_dir, 'index.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(str(soup.prettify()))
            
            self.logger.info('Website cloned successfully!')
            return {
                'images': images,
                'css_file': combined_css,
                'js_file': combined_js
            }
            
        except Exception as e:
            self.logger.error(f'Error cloning website: {str(e)}')
            return None
