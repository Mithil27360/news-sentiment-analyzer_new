from flask import Flask, render_template, request, url_for, redirect, flash
import newspaper
from newspaper import Article, Source
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
import logging
import time
import re
import validators
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import os
import traceback
import sys
from collections import Counter

# Add this near the top of your app.py file after creating the Flask app
app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24)  # For flash messages
# Set up basic exception handling to print to console
def exception_handler(exctype, value, tb):
    print(''.join(traceback.format_exception(exctype, value, tb)))


sys.excepthook = exception_handler

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For flash messages

# --- NLTK Sentiment Analyzer Setup ---
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except (LookupError, nltk.downloader.DownloadError):
    logger.info("Downloading NLTK vader_lexicon...")
    nltk.download('vader_lexicon')

try:
    nltk.data.find('tokenizers/punkt')
except (LookupError, nltk.downloader.DownloadError):
    logger.info("Downloading NLTK punkt tokenizer...")
    nltk.download('punkt')

analyzer = SentimentIntensityAnalyzer()


# --- URL and Validation Helper Functions ---

def normalize_url(url):
    """Normalize URL to ensure it has a scheme."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


# --- Article Scraping Functions ---

def get_article_urls_from_source(source_url, max_articles=10):
    """
    Fetches article URLs from a given news source URL.
    Uses multiple strategies if newspaper3k fails.
    """
    logger.info(f"Building source for: {source_url}")
    urls = []

    # Try using newspaper3k first
    try:
        config = newspaper.Config()
        config.memoize_articles = False
        config.request_timeout = 20
        config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

        source = Source(source_url, config=config)
        source.build()

        if hasattr(source, 'articles') and source.articles:
            logger.info(f"Found {len(source.articles)} potential articles from source using newspaper3k.")
            urls = [article.url for article in source.articles[:max_articles]]
        else:
            logger.warning("No articles found with newspaper3k, trying direct HTML parsing.")
    except Exception as e:
        logger.error(f"Error with newspaper3k source building: {e}")

    # If newspaper3k didn't find any URLs, try direct HTML parsing
    if not urls:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(source_url, headers=headers, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            base_domain = urlparse(source_url).netloc

            # Look for anchor tags - common article link patterns
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']

                # Normalize URL if it's a relative path
                if href.startswith('/'):
                    href = f"https://{base_domain}{href}"
                elif not href.startswith(('http://', 'https://')):
                    # Skip internal page anchors, javascript, etc.
                    if href.startswith('#') or href.startswith('javascript:'):
                        continue
                    href = f"{source_url.rstrip('/')}/{href.lstrip('/')}"

                # Exclude common non-article paths
                if any(x in href.lower() for x in
                       ['/tag/', '/category/', '/author/', '/about/', '/contact/', '/search/', '/page/']):
                    continue

                # Look for common article URL patterns
                if re.search(r'/\d{4}/\d{2}/|/article/|/story/|/news/|\.html$|\.htm$', href):
                    if href not in urls and base_domain in href:
                        urls.append(href)

            logger.info(f"Found {len(urls)} potential article URLs using direct HTML parsing.")
            urls = urls[:max_articles]  # Limit to max_articles

        except Exception as e:
            logger.error(f"Error with direct HTML parsing: {e}")

    if not urls:
        logger.warning("Could not find any article URLs using either method.")
    else:
        logger.info(f"Processing up to {len(urls)} articles.")

    return urls


def scrape_article_content(article_url):
    """
    Scrapes the title and main text content of a single article.
    Falls back to BeautifulSoup if newspaper3k fails.
    """
    logger.info(f"Scraping article: {article_url}")

    # Try newspaper3k first
    try:
        article = Article(article_url)
        article.download()
        article.parse()

        title = article.title
        text = article.text

        if title and text and len(text) > 100:  # Basic validation
            return title, text
        else:
            logger.warning(
                f"newspaper3k extracted insufficient content: title_len={len(title) if title else 0}, text_len={len(text) if text else 0}")
    except Exception as e:
        logger.error(f"Error with newspaper3k for {article_url}: {e}")

    # Fall back to BeautifulSoup if newspaper3k failed
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(article_url, headers=headers, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract title - common patterns
        title = None
        if soup.title and soup.title.text:
            title = soup.title.text.strip()
        else:
            title_tag = soup.find('h1') or soup.find('meta', property='og:title') or soup.find('meta',
                                                                                               attrs={'name': 'title'})
            if title_tag:
                if title_tag.name == 'meta':
                    title = title_tag.get('content', '')
                else:
                    title = title_tag.get_text()

        # Extract article content - multiple common patterns
        content = ""

        # Look for article body in common containers
        article_containers = [
            soup.find('article'),
            soup.find('div', class_=lambda c: c and any(
                x in str(c).lower() for x in ['article', 'content', 'story', 'body', 'text', 'post'])),
            soup.find('section',
                      class_=lambda c: c and any(x in str(c).lower() for x in ['article', 'content', 'story', 'body']))
        ]

        for container in article_containers:
            if container:
                # Try to exclude non-content elements
                for el in container.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    el.decompose()

                # Extract paragraphs
                paragraphs = container.find_all('p')
                content = ' '.join(p.get_text().strip() for p in paragraphs)

                if len(content) > 200:  # If we got a reasonable amount of content
                    break

        if title and content and len(content) > 200:
            return title, content
        else:
            logger.warning(
                f"BeautifulSoup extracted insufficient content: title_len={len(title) if title else 0}, content_len={len(content)}")
            return None, None

    except Exception as e:
        logger.error(f"Error with BeautifulSoup for {article_url}: {e}")
        return None, None


# --- Analysis Functions ---

def get_sentiment_analysis(text):
    """
    Analyzes the sentiment of a given text using NLTK VADER.
    Provides more detailed reasoning.
    """
    if not text or not text.strip():
        return {"sentiment_label": "N/A", "reason": "No text provided for analysis.", "score": 0}

    # Split into sentences for detailed analysis
    sentences = nltk.sent_tokenize(text)

    # Get overall sentiment
    overall_scores = analyzer.polarity_scores(text)
    compound_score = overall_scores['compound']

    if compound_score >= 0.05:
        sentiment_label = "Positive"
    elif compound_score <= -0.05:
        sentiment_label = "Negative"
    else:
        sentiment_label = "Neutral"

    # Find most positive and most negative sentences for reasoning
    most_positive_score = -1
    most_positive_sent = ""
    most_negative_score = 1
    most_negative_sent = ""

    for sentence in sentences:
        if len(sentence) < 10:  # Skip very short sentences
            continue

        sent_scores = analyzer.polarity_scores(sentence)

        if sent_scores['compound'] > most_positive_score:
            most_positive_score = sent_scores['compound']
            most_positive_sent = sentence

        if sent_scores['compound'] < most_negative_score:
            most_negative_score = sent_scores['compound']
            most_negative_sent = sentence

    # Create reasoning based on overall sentiment
    reason = f"Overall sentiment score: {compound_score:.2f}. "

    if sentiment_label == "Positive" and most_positive_score > 0:
        reason += f"Example positive statement: '{most_positive_sent}'"
    elif sentiment_label == "Negative" and most_negative_score < 0:
        reason += f"Example negative statement: '{most_negative_sent}'"
    else:
        reason += "The article contains a balanced mix of positive and negative elements or uses neutral language."

    return {"sentiment_label": sentiment_label, "reason": reason, "score": compound_score}


def categorize_article(title, content):
    """Categorize articles based on keywords in title and content"""
    # Define categories and their related keywords
    categories = {
        'Politics': ['government', 'election', 'president', 'minister', 'parliament', 'congress', 'policy', 'political',
                     'vote', 'campaign', 'brexit', 'eu', 'deal'],
        'Business': ['economy', 'market', 'stock', 'finance', 'business', 'company', 'industry', 'trade', 'investment',
                     'economic'],
        'Technology': ['tech', 'technology', 'digital', 'software', 'app', 'computer', 'cyber', 'internet', 'online',
                       'ai', 'artificial intelligence', 'robot', 'driverless'],
        'Health': ['health', 'covid', 'virus', 'medical', 'doctor', 'hospital', 'patient', 'disease', 'treatment',
                   'cancer', 'vaccine'],
        'Sports': ['sport', 'football', 'soccer', 'tennis', 'match', 'championship', 'game', 'player', 'team',
                   'tournament', 'olympic'],
        'Entertainment': ['film', 'movie', 'music', 'celebrity', 'actor', 'entertainment', 'star', 'television', 'tv',
                          'hollywood', 'show', 'concert'],
        'Science': ['science', 'research', 'scientist', 'study', 'discovery', 'space', 'planet', 'climate',
                    'environment', 'physics', 'biology'],
        'World': ['world', 'international', 'foreign', 'global', 'country', 'nation', 'war', 'conflict', 'crisis']
    }

    # Combine title and first part of content for analysis
    text = (title + " " + content[:500]).lower()

    # Count keyword matches for each category
    scores = {}
    for category, keywords in categories.items():
        score = sum(1 for keyword in keywords if re.search(r'\b' + keyword + r'\b', text))
        scores[category] = score

    # Return the category with the highest score, or "General" if no clear match
    max_score = max(scores.values()) if scores else 0
    if max_score > 0:
        # Get all categories with the maximum score
        top_categories = [category for category, score in scores.items() if score == max_score]
        return top_categories[0]  # Return the first category if there's a tie
    else:
        return "General"


# --- Route Handlers ---

@app.route('/', methods=['GET'])
def index():
    """Renders the homepage with the input form."""
    return render_template('index.html')


@app.route('/sources')
def news_sources():
    """Provides a list of popular news sources for easy access."""
    sources = [
        {"name": "BBC News", "url": "https://www.bbc.com/news"},
        {"name": "Reuters", "url": "https://www.reuters.com"},
        {"name": "The Guardian", "url": "https://www.theguardian.com"},
        {"name": "NPR", "url": "https://www.npr.org/sections/news/"},
        {"name": "Al Jazeera", "url": "https://www.aljazeera.com"},
        {"name": "CNN", "url": "https://www.cnn.com"},
        {"name": "Fox News", "url": "https://www.foxnews.com"},
        {"name": "CNBC", "url": "https://www.cnbc.com"},
        {"name": "The New York Times", "url": "https://www.nytimes.com"}
    ]
    return render_template('sources.html', sources=sources)


@app.route('/analyze', methods=['POST'])
def analyze_website():
    """
    Handles the form submission, scrapes articles, analyzes sentiment,
    and renders the results page.
    """
    news_source_url = request.form.get('news_url', '').strip()
    max_articles_to_process = min(int(request.form.get('max_articles', 5)), 20)  # Default 5, max 20

    if not news_source_url:
        flash("Please provide a news website URL.", "error")
        return redirect(url_for('index'))

    # Validate URL
    news_source_url = normalize_url(news_source_url)
    if not validators.url(news_source_url):
        flash("Please enter a valid URL.", "error")
        return redirect(url_for('index'))

    logger.info(f"Analyzing: {news_source_url} (max articles: {max_articles_to_process})")
    analyzed_articles_data = []

    # Track categories distribution
    categories_count = Counter()

    try:
        # Get article URLs
        article_urls = get_article_urls_from_source(news_source_url, max_articles=max_articles_to_process)

        if not article_urls:
            flash("Could not find any article links on the provided website.", "error")
            return render_template('results.html',
                                   source_url=news_source_url,
                                   articles=[],
                                   error_message="No article links were found. This might not be a news website or the scraping method couldn't detect articles.")

        # Process each article
        successful_articles = 0
        sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0, "N/A": 0}

        for i, url in enumerate(article_urls):
            logger.info(f"Processing article {i + 1}/{len(article_urls)}: {url}")
            title, text_content = scrape_article_content(url)

            if title and text_content:
                # Get sentiment analysis
                sentiment_info = get_sentiment_analysis(text_content)
                sentiment_counts[sentiment_info["sentiment_label"]] += 1

                # Get category
                category = categorize_article(title, text_content)
                categories_count[category] += 1

                analyzed_articles_data.append({
                    "title": title,
                    "url": url,
                    "sentiment": sentiment_info["sentiment_label"],
                    "reason": sentiment_info["reason"],
                    "score": sentiment_info["score"],
                    "category": category,
                    "text_preview": text_content[:300] + "..." if len(text_content) > 300 else text_content
                })
                successful_articles += 1
            elif title:  # If we got a title but no text
                sentiment_counts["N/A"] += 1
                analyzed_articles_data.append({
                    "title": title,
                    "url": url,
                    "sentiment": "N/A",
                    "reason": "Could not extract text content for analysis.",
                    "score": 0,
                    "category": "Unknown",
                    "text_preview": "Content extraction failed."
                })

        logger.info(f"Successfully analyzed {successful_articles} out of {len(article_urls)} articles.")

        if not analyzed_articles_data:
            flash("No articles could be successfully analyzed.", "error")
            return render_template('results.html',
                                   source_url=news_source_url,
                                   articles=[],
                                   error_message="Found some article links, but couldn't extract content from any of them.")

    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        flash(f"An error occurred: {str(e)}", "error")
        return render_template('results.html',
                               source_url=news_source_url,
                               articles=[],
                               error_message=f"An error occurred during processing: {str(e)}")

    return render_template('results.html',
                           source_url=news_source_url,
                           articles=analyzed_articles_data,
                           article_count=len(analyzed_articles_data),
                           total_attempted=len(article_urls),
                           sentiment_counts=sentiment_counts,
                           categories=dict(categories_count))


if __name__ == '__main__':
    print("News Sentiment Analyzer starting...")
    print("Access the application at http://127.0.0.1:5001/")
    app.run(debug=True, host='0.0.0.0', port=5001)