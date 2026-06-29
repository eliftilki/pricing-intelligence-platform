# Data ingestion service uses the same 12-hour cache window. Candidate and
# feature queries must not consume older listings even if historical tier
# records remain in the database.
COMPETITOR_DATA_MAX_AGE_HOURS = 12
