import unittest
import sys
import os

# Add src to path to import ingest_normalized
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from ingest_normalized import normalize_url
except ImportError:
    # Falback if running from root
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
    from ingest_normalized import normalize_url

class TestNormalizeUrl(unittest.TestCase):

    def test_basic_normalization(self):
        # Case 1: Protocol removal
        self.assertEqual(normalize_url("https://bushido-sport.pl"), "bushido-sport.pl")
        self.assertEqual(normalize_url("http://bushido-sport.pl"), "bushido-sport.pl")
        
        # Case 2: www removal
        self.assertEqual(normalize_url("https://www.bushido-sport.pl"), "bushido-sport.pl")
        self.assertEqual(normalize_url("www.bushido-sport.pl"), "bushido-sport.pl")

    def test_trailing_slash(self):
        self.assertEqual(normalize_url("bushido-sport.pl/buty/"), "bushido-sport.pl/buty")
        self.assertEqual(normalize_url("bushido-sport.pl/buty"), "bushido-sport.pl/buty")

    def test_query_params(self):
        # UTMs
        self.assertEqual(normalize_url("bushido-sport.pl/buty?utm_source=fb"), "bushido-sport.pl/buty")
        self.assertEqual(normalize_url("bushido-sport.pl/buty?fbclid=12345"), "bushido-sport.pl/buty")
        self.assertEqual(normalize_url("bushido-sport.pl/buty?utm_source=fb&utm_medium=cpc"), "bushido-sport.pl/buty")
        
        # Other params - should be stripped as per "Landing Page as Product" logic?
        # A product URL with ?variant=1 might be distinct, but usually Ads point to the main product.
        # For now, stripping ALL params is the safest for joining with Feed.
        self.assertEqual(normalize_url("bushido-sport.pl/buty?variant=123"), "bushido-sport.pl/buty")

    def test_case_sensitivity(self):
        self.assertEqual(normalize_url("Bushido-Sport.pl/Buty"), "bushido-sport.pl/buty")

    def test_real_examples_bushido(self):
        self.assertEqual(normalize_url("https://bushido-sport.pl/product-pol-123-Rekawice.html"), "bushido-sport.pl/product-pol-123-rekawice.html")
        
    def test_real_examples_iiyama(self):
        self.assertEqual(normalize_url("https://iiyama-sklep.pl/g-master"), "iiyama-sklep.pl/g-master")

    def test_real_examples_koszulkowy(self):
        self.assertEqual(normalize_url("https://koszulkowy.pl/"), "koszulkowy.pl")

if __name__ == '__main__':
    unittest.main()
