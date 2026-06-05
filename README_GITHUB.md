---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 247a3b775cfbfe96972e0569cde92088_6a626ac960e411f19f62525400d9a7a1
    ReservedCode1: TWECKRxl/fIvkAsFrlMaUlxpjiW1LpM+M7DnC4S2NYqAgyyb6tKmrwEFMcIhK1d/x5SARoBsSlULIxSqChi8dk3DcsTxofnyl70Kgylca/kAOU0IFtfiYGKvkMJqPq6sYdGha7S9UYM3z4mF5bqnIQ7M/87ZcqAvEJNeQclCaQNjqTiOJnLjNfUfIkI=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 247a3b775cfbfe96972e0569cde92088_6a626ac960e411f19f62525400d9a7a1
    ReservedCode2: TWECKRxl/fIvkAsFrlMaUlxpjiW1LpM+M7DnC4S2NYqAgyyb6tKmrwEFMcIhK1d/x5SARoBsSlULIxSqChi8dk3DcsTxofnyl70Kgylca/kAOU0IFtfiYGKvkMJqPq6sYdGha7S9UYM3z4mF5bqnIQ7M/87ZcqAvEJNeQclCaQNjqTiOJnLjNfUfIkI=
---

# 🍽️ Restaurant Review AI

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Build](https://img.shields.io/badge/build-passing-brightgreen)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

**Restaurant Review AI** is a lightweight NLP tool that analyzes negative restaurant reviews. It extracts sentiment polarity, identifies key complaint categories, and generates actionable AI-powered reply suggestions — helping restaurant owners respond faster and smarter.

---

## ✨ Features

- **Sentiment Analysis** – Classifies review sentiment as positive, neutral, or negative (with confidence score).
- **Problem Categorization** – Detects common complaint types such as *food quality*, *service delay*, *cleanliness*, *pricing*, and *ambiance*.
- **AI Reply Suggestion** – Generates context-aware, empathetic draft replies for negative reviews.
- **Extensible Pipeline** – Modular design allows easy integration of custom classifiers or LLM backends.
- **Minimal Dependencies** – Built on Hugging Face Transformers and scikit-learn.

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/yourusername/restaurant-review-ai.git
cd restaurant-review-ai
pip install -r requirements.txt
```

### Usage Example

```python
from review_ai import ReviewAnalyzer

analyzer = ReviewAnalyzer()

review = "The food was cold and the waiter was rude. Never coming back."

result = analyzer.analyze(review)

print(result.sentiment)        # negative
print(result.confidence)       # 0.96
print(result.categories)       # ['food_quality', 'service']
print(result.reply_suggestion) # "We sincerely apologize for your experience..."
```

---

## 📚 API Documentation

### `ReviewAnalyzer`

#### `__init__(model_name: str = "distilbert-base-uncased")`
Initializes the analyzer with a pretrained transformer model.

#### `analyze(text: str) -> AnalysisResult`
Returns an `AnalysisResult` object with the following fields:

| Field              | Type     | Description                                      |
|--------------------|----------|--------------------------------------------------|
| `sentiment`        | `str`    | One of `positive`, `neutral`, `negative`         |
| `confidence`       | `float`  | Confidence score of the sentiment prediction     |
| `categories`       | `List[str]` | List of detected problem categories (e.g., `food_quality`, `service`) |
| `reply_suggestion` | `str`    | AI-generated draft reply for the negative review |

#### `batch_analyze(texts: List[str]) -> List[AnalysisResult]`
Processes multiple reviews in batch for higher throughput.

---

## 📸 Example Output

**Input:**
> "I waited 40 minutes for my pizza, and when it arrived it was burnt. The manager didn't even apologize."

**Output:**
```json
{
  "sentiment": "negative",
  "confidence": 0.98,
  "categories": ["service_delay", "food_quality"],
  "reply_suggestion": "Hi [Customer], we're truly sorry for the long wait and the burnt pizza. This is not the experience we want for our guests. We'd like to make it right — please contact us at [email] so we can offer a complimentary meal. Thank you for your feedback."
}
```

---

## 🤝 Contributing

We welcome contributions from the community! To contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a Pull Request.

Please ensure your code follows the existing style and includes tests where applicable.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for restaurant owners and customer experience teams.**
*（内容由AI生成，仅供参考）*
