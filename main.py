from scraper import WebScraper
import config
import logging
import os

def main():
    try:
        url = input("Enter website URL: ")
        scraper = WebScraper(url)
        
        print('Starting scraping process...')
        data = scraper.scrape()
        
        if data:
            print(f'''
Scraping completed successfully:
- Images: {len(data["images"])}
- Headers: {len(data["headers"])}
- Paragraphs: {len(data["paragraphs"])}
- Links: {len(data["links"])}

Data saved in: {scraper.base_dir}
''')
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
    finally:
        if 'scraper' in locals():
            del scraper

if __name__ == '__main__':
    main()
