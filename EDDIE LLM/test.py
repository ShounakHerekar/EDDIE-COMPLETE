# test.py
import json

# Hardcoded dispatch response
dispatch_output = {'status': 'success', 'results': {'filings_summary': {'count': 1, 'filings': [{'form': '10-K', 'filing_date': '2024-02-02', 'accession_number': '0001018724-24-000008', 'filing_url': 'https://www.sec.gov/Archives/edgar/data/1018724/000101872424000008/amzn-20231231.htm'}]}}}
def test_extract_filing_url(data):
    print("\n🔍 Testing Filing URL Extraction...\n")

    try:
        filings = data["results"]["filings_summary"]["filings"]

        if not filings:
            print("⚠️ No filings found.")
            return

        filing = filings[0]
        print(filing)
        filing_url = filing.get("filing_url")
        print(filing_url)

        if filing_url:
            print("✅ Filing URL extracted successfully:")
            print(f"   {filing_url}")
            return filing_url
        else:
            print("❌ Filing URL missing from JSON")

    except KeyError as e:
        print(f"❌ Missing key in JSON: {e}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    test_extract_filing_url(dispatch_output)
