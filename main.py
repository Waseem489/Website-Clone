from scraper import WebScraper
import logging
import os

def main():
    try:
        url = input("Enter website URL: ")
        scraper = WebScraper(url)
        
        print('Starting website cloning...')
        data = scraper.clone_website()
        
        if data:
            print(f'''
Website cloned successfully:
- Images: {len(data["images"])}
- CSS files: {len(data["css_files"])}
- JavaScript files: {len(data["js_files"])}

Files saved in: {scraper.base_dir}

Folder structure:
- {scraper.base_dir}/
  ├── images/    (Downloaded images)
  ├── css/       (Stylesheet files)
  ├── js/        (JavaScript files)
  └── index.html (Main HTML file)
''')
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
    finally:
        if 'scraper' in locals():
            del scraper

if __name__ == '__main__':
    main()
