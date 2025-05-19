# News Sentiment Analyzer

A Flask-based application that analyzes sentiment in news articles from various online sources.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Screenshots](#screenshots)
- [Demo](#demo)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Technologies Used](#technologies-used)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## Overview

**News Sentiment Analyzer** is a web app built with Flask that lets you input URLs of news articles and instantly view a sentiment analysis (positive, negative, neutral) of their content. It aggregates, classifies, and visualizes sentiment trends across multiple sources.

---

## Features

- 🔎 Analyze sentiment of any news article URL  
- 📊 Dashboard with sentiment trends and statistics  
- 📰 Multi-source support  
- 🏷️ Content categorization  
- 🏷️ Entity extraction (people, places, organizations)  
- ⚡ Fast, asynchronous processing  
- 💾 Database storage for historical trends  
- 📈 Visual analytics

---

## Screenshots

> _Add screenshots of your app here!_
>
> ![Dashboard Screenshot](static/screenshots/dashboard.png)
> ![Sentiment Results](static/screenshots/results.png)

---

## Demo

> _Add a link to your live app if hosted, or a demo video_
>
> [Live Demo](https://your-demo-link.com)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/mithilmitmpl/news-sentiment-analyzer_new.git
cd news-sentiment-analyzer_new

# (Optional) Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize the database
flask init-db
```

---

## Usage

```bash
python app.py
```
Then open your browser and go to [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

---

## Project Structure

```plaintext
.
├── app.py
├── modules/
│   ├── __init__.py
│   ├── scraper.py
│   ├── sentiment.py
│   └── impact.py
├── static/
│   └── js/
│       └── main.js
├── templates/
│   ├── index.html
│   ├── results.html
│   └── sources.html
├── requirements.txt
├── schema.sql
├── LICENSE
└── README.md
```

---

## Technologies Used

- Python 3.8+
- Flask
- NLTK
- newspaper3k
- aiohttp
- BeautifulSoup4
- requests
- validators

---

## Contributing

1. Fork the repository
2. Create your branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a pull request

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Contact

Created by [mithilmitmpl](https://github.com/mithilmitmpl)  
Open an issue for support or feature requests!
