"""Flask web application for the Internal Linking Suggestion Tool."""

import csv
import io
from datetime import datetime

from flask import Flask, render_template, request, jsonify, Response

from .config import Config
from .dataforseo_client import AuthenticationError
from .gemini_extractor import GeminiError
from .link_finder import InternalLinkFinder
from .scraper import ScrapingError
from .utils import validate_url

app = Flask(__name__)


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze a URL for internal linking opportunities using Gemini AI."""
    data = request.get_json()
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'error': 'Please enter a URL'}), 400

    if not validate_url(url):
        return jsonify({'error': 'That doesn\'t look like a real URL. Try again.'}), 400

    try:
        Config.validate()
    except ValueError as e:
        return jsonify({'error': str(e)}), 500

    try:
        finder = InternalLinkFinder()
        suggestions, errors = finder.find_opportunities(source_url=url)

        results = []
        for s in suggestions:
            target_urls = [
                {'url': t.url, 'title': t.title, 'position': t.position}
                for t in s.target_urls
            ]
            results.append({
                'anchor_text': s.anchor_text,
                'target_urls': target_urls
            })

        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'errors': errors,
            'source_url': url
        })

    except AuthenticationError as e:
        return jsonify({'error': f'DataForSEO auth failed: {str(e)}'}), 401
    except GeminiError as e:
        return jsonify({'error': f'Gemini AI hiccup: {str(e)}'}), 500
    except ScrapingError as e:
        return jsonify({'error': f'Couldn\'t scrape that page: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Something broke: {str(e)}'}), 500


@app.route('/export-csv', methods=['POST'])
def export_csv():
    """Export results to CSV."""
    data = request.get_json()
    results = data.get('results', [])
    source_url = data.get('source_url', '')

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Proposed Anchor Text', 'Target URL 1', 'Target URL 2', 'Target URL 3', 'Source URL'])

    for r in results:
        target_urls = r.get('target_urls', [])
        writer.writerow([
            r.get('anchor_text', ''),
            target_urls[0]['url'] if len(target_urls) > 0 else '',
            target_urls[1]['url'] if len(target_urls) > 1 else '',
            target_urls[2]['url'] if len(target_urls) > 2 else '',
            source_url
        ])

    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=links_{timestamp}.csv'}
    )


def run_app(host='127.0.0.1', port=5000, debug=False):
    """Run the Flask application."""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_app(debug=True)
