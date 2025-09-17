# steamdb-scraper-sentiment-analysis-VAR

This study explores integrating sentiment analysis into churn forecasting for online multiplayer
games, building on the research of Rahman et al. (2024). While traditional churn models rely
solely on player count data, this study investigates whether incorporating player sentiment scores
derived from Steam reviews can improve the prediction of player churn. Focusing on three of
Steam’s most popular multiplayer competitive games (CS 2, Dota 2, and PUBG), a Vector
Autoregression (VAR) model was used to analyze the dynamic interplay between player
sentiment and engagement. In addition to replicating prior models, this study extends them to a
broader set of games, demonstrating the practical value of sentiment-driven forecasting for game
developers to anticipate and mitigate player churn.

Due to the limitations of the Steam API, individual users can only extract review data within a
maximum time range of the most recent one-month period. Therefore, this study collected 100
randomly sampled reviews per day from November 11 to December 11, 2024, using Python web
scraping techniques. The first 25 days of review data were used for model training, while the
remaining 5 days were used for forecasting and evaluation. The sentiment score for each day was
calculated as the ratio of positive reviews to total reviews. (For the detailed code, please see the
attachment “WebScrapingSteamAPI.py.”)
