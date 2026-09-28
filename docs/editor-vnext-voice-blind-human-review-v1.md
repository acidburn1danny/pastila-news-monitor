# VNext VOICE Blind Human Review Capture v1

Localhost-only, standard-library capture tool for the 216 frozen blind items. It renders factual setup and commentary, validates only human-entered values against the frozen score schema, and creates one atomic content-addressed receipt per blind output. It contains no answer key, candidate mapping, automated scoring, aggregation, unseal, or model-selection capability.

The receipts root belongs under `/root/pastila-vnext/v1/reviews/voice-blind-v1/receipts`. Run `--preflight` before serving. Completion at 216 receipts still requires the separately published completion gate; this tool must stop before unseal.
