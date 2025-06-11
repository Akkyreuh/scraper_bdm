import requests
from bs4 import BeautifulSoup
import pymongo
import re
from datetime import datetime

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["blog_du_moderateur"]
collection = db["articles"]

def extract_img_url(img_tag):
    if not img_tag:
        return None
    for attr in ['data-lazy-src', 'data-src', 'src']:
        if img_tag.has_attr(attr):
            url = img_tag[attr]
            if url.startswith('http'):
                return url
    return None

def extract_images_from_article(content_div):
    images = []
    if not content_div:
        return images
    for figure in content_div.find_all('figure'):
        img_url = None
        caption = ''
        link = figure.find('a', href=True)
        img = figure.find('img')
        if link and img:
            img_url = link['href']
        elif img:
            img_url = img.get('src') or img.get('data-lazy-src')
        figcaption = figure.find('figcaption')
        if figcaption:
            caption = figcaption.get_text(" ", strip=True)
        elif img and img.has_attr('alt'):
            caption = img['alt']
        if img_url:
            images.append({'url': img_url, 'caption': caption})
    for img in content_div.find_all('img'):
        if not img.find_parent('figure'):
            img_url = img.get('src') or img.get('data-lazy-src')
            caption = img.get('alt') or img.get('title', '')
            if img_url and img_url.startswith('http'):
                images.append({'url': img_url, 'caption': caption})
    return images

def fetch_article_details(article_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(article_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        author = None
        author_div = soup.find('div', class_='author-meta')
        if author_div:
            a_tag = author_div.find('a', class_='author-name')
            if a_tag:
                author = a_tag.get_text(strip=True)
        if not author:
            byline_span = soup.find('span', class_='byline')
            if byline_span:
                author = byline_span.get_text(strip=True)
        
        content_div = soup.find('div', class_='entry-content row justify-content-center')
        content_text = None
        if content_div:
            for tag in content_div.find_all(['script', 'style', 'iframe', 'form']):
                tag.decompose()
            p_tags = content_div.find_all('p')
            content_text = ' '.join([p.get_text(" ", strip=True) for p in p_tags if p.get_text(strip=True)])
            content_text = re.sub(r'\s+', ' ', content_text).strip()
        article_images = extract_images_from_article(content_div)
        return {
            'author': author,
            'content': content_text,
            'article_images': article_images
        }
    except Exception as e:
        print(f"Error fetching article details: {e}")
        return {'author': None, 'content': None, 'article_images': []}
    
    
def fetch_articles(url, category):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        articles_data = []

        main_tag = soup.find('main')
        articles = main_tag.find_all('article')
        for article in articles:
            img_div = article.find('div', class_='post-thumbnail picture rounded-img')
            img_tag = img_div.find('img') if img_div else None
            img_url = extract_img_url(img_tag)

            meta_div = article.find('div', class_='entry-meta ms-md-5 pt-md-0 pt-3')
            tag = meta_div.find('span', class_='favtag color-b').get_text(strip=True) if meta_div else None
            date_text = meta_div.find('span', class_='posted-on t-def px-3').get_text(strip=True) if meta_div else None

            header = meta_div.find('header', class_='entry-header pt-1') if meta_div else None
            a_tag = header.find('a') if header else None
            article_url = a_tag['href'] if a_tag and a_tag.has_attr('href') else None
            title = a_tag.find('h3').get_text(strip=True) if a_tag and a_tag.find('h3') else None

            summary_div = meta_div.find('div', class_='entry-excerpt t-def t-size-def pt-1') if meta_div else None
            summary = summary_div.get_text(strip=True) if summary_div else None

            formatted_date = None
            if date_text:
                try:
                    months = {
                        'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04', 'mai': '05', 'juin': '06', 
                        'juillet': '07', 'août': '08', 'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
                    }
                    parts = date_text.split()
                    if len(parts) >= 3:
                        day = parts[0].zfill(2)
                        month = months.get(parts[1].lower())
                        year = parts[2]
                        if day and month and year:
                            formatted_date = f"{year}/{month}/{day}"
                except:
                    formatted_date = None

            article_content = {}
            if article_url:
                article_content = fetch_article_details(article_url)

            article_data = {
                'title': title,
                'image': img_url,
                'subcategory': tag,
                'resume': summary,
                'date': formatted_date,
                'author': article_content.get('author'),
                'content': article_content.get('content'),
                'article_images': article_content.get('article_images', []),
                'url': article_url,
                'category': category
            }
            
            articles_data.append(article_data)
            
            if article_url:
                collection.update_one(
                    {'url': article_url},
                    {'$set': article_data},
                    upsert=True
                )

        return articles_data

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return []

def get_articles_by_category(category):
    return list(collection.find({"category": category}))

def get_articles_by_subcategory(subcategory):
    return list(collection.find({"subcategory": subcategory}))

categories = ['web', 'marketing', 'social', 'tech']
base_url = "https://www.blogdumoderateur.com/"

for category in categories:
    full_url = base_url + category + "/"
    print(f"====================== {category} ======================")
    articles = fetch_articles(full_url, category)

    for i, article in enumerate(articles, 1):
        print(f"\nArticle {i}:")
        for key, value in article.items():
            print(f"{key.capitalize()}: {value}")
