import requests
from bs4 import BeautifulSoup

def fetch_articles(url):
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
            date = meta_div.find('span', class_='posted-on t-def px-3').get_text(strip=True) if meta_div else None

            header = meta_div.find('header', class_='entry-header pt-1') if meta_div else None
            a_tag = header.find('a') if header else None
            article_url = a_tag['href'] if a_tag and a_tag.has_attr('href') else None
            title = a_tag.find('h3').get_text(strip=True) if a_tag and a_tag.find('h3') else None

            summary_div = meta_div.find('div', class_='entry-excerpt t-def t-size-def pt-1') if meta_div else None
            summary = summary_div.get_text(strip=True) if summary_div else None

            articles_data.append({
                'image': img_url,
                'tag': tag,
                'date': date,
                'url': article_url,
                'title': title,
                'résumé': summary
            })

        return articles_data

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return []

def extract_img_url(img_tag):
    if not img_tag:
        return None
    for attr in ['data-lazy-src', 'data-src', 'src']:
        if img_tag.has_attr(attr):
            url = img_tag[attr]
            if url.startswith('https://'):
                return url
    return None

categories = ['web', 'marketing', 'social', 'tech']
base_url = "https://www.blogdumoderateur.com/"

for category in categories:
    full_url = base_url + category + "/"
    print(f"====================== {category} ======================")
    articles = fetch_articles(full_url)

    for i, article in enumerate(articles, 1):
        print(f"\nArticle {i}:")
        for key, value in article.items():
            print(f"{key.capitalize()}: {value}")
