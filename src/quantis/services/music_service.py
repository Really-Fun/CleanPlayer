from quantis.services import AsyncDownloader, AsyncFinder, AsyncRecommendation, AsyncStreamer
from quantis.providers import PathProvider

class MusicService:
    
    def __init__(self):
        self._downloader = AsyncDownloader()
        self._finder = AsyncFinder()
        self._recommendation = AsyncRecommendation()
        self._streamer = AsyncStreamer()
        self._provider = PathProvider()
        
    @property
    def downloader(self):
        return self._downloader

    @property
    def finder(self):
        return self._finder
    
    @property
    def recommendation(self):
        return self._recommendation
    
    @property
    def streamer(self):
        return self._streamer
    
    @property
    def provider(self):
        return self._provider