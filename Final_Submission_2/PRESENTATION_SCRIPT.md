# 10-15 Minute Presentation Script

## 1. Introduction and Motivation

Our project asks whether satellite-detected thermal anomalies can help monitor armed conflict risks in regions important to maritime shipping and energy markets. We selected the Black Sea, Red Sea/Yemen, Persian Gulf, and Eastern Mediterranean because disruptions in these regions can affect route planning, insurance premiums, fuel prices, and energy supply.

## 2. Data Collection

We collected NASA FIRMS VIIRS thermal anomaly detections from 2024-01-01 to 2024-06-30. After cleaning, the database contained 265,321 FIRMS detections. We also collected 3,724 conflict-related news articles from GDELT, Google News RSS, and Bing News RSS using keywords such as war, conflict, airstrike, shelling, missile, attack, explosion, and combat.

## 3. Database Pipeline

All core outputs were stored in PostgreSQL using Docker. The required tables are firms_detections, news_articles, thermal_events, and event_matches. This makes the workflow closer to a real monitoring pipeline because later analysis reads from stored database tables rather than only from in-memory data.

## 4. Thermal Event Clustering

Raw FIRMS detections are individual satellite pixels, so we clustered nearby detections into thermal events using a 10 km spatial radius and a 2 day temporal window. This produced 2,904 thermal events. For each event, we computed centroid coordinates, start and end dates, duration, total FRP, maximum brightness, number of detections, night-detection ratio, and region.

## 5. News Matching and Regional Coverage

Thermal events were matched to conflict news if articles appeared in the same region within a 0 to 7 day window and contained conflict-related keywords. The strongest association rate was in Ukraine_Black_Sea. The main blind spot by thermal-events-per-article score was Eastern_Mediterranean, which suggests satellite monitoring is especially useful where reporting is comparatively sparse.

## 6. Machine Learning

We trained Logistic Regression, Decision Tree, Gaussian Naive Bayes, and SVM classifiers to predict whether a thermal event was conflict-associated. The best F1 score in this run came from SVM with F1 = 0.950. In shipping-risk monitoring, recall is especially important because missing a real conflict signal can expose vessels and cargo to operational risk.

## 7. Dashboard Walkthrough

The dashboard includes a map of thermal events colored by conflict association, a regional association-rate comparison, a monthly event trend, and a blind-spot panel showing regions where satellite monitoring adds value because news coverage is sparse. The headline finding is that satellite thermal anomalies reveal conflict-risk signals unevenly covered by news.

## 8. Conclusions

The project shows that FIRMS thermal anomalies are not a standalone conflict detector, but they are valuable as part of a multi-source monitoring system. A shipping company could use this pipeline as an early-warning layer for route review, insurance planning, and fuel-risk monitoring.
