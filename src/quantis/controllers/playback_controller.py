from __future__ import annotations

from quantis.player import Player
from quantis.providers import PlaylistManager
from quantis.services import MusicService
from quantis.models import Track

class PlaybackController:
    """Медиатор логики воспроизведения. 
    
    Связывает независимый плеер, менеджер плейлистов и единый музыкальный сервис.
    """
    def __init__(self, player: Player, playlist_manager: PlaylistManager, music_service: MusicService):
        self.player = player
        self.playlist_manager = playlist_manager
        self.music = music_service

    async def play_track(self, track: Track | None) -> None:
        if not track: 
            return
        
        if track.downloaded:
            ext = getattr(track, "extension", None)
            source = self.music.provider.get_track_path(track, ext) if ext else self.music.provider.get_track_path(track)
        else:
            source = await self.music.streamer.get_stream_url(track)

        if source:
            self.player.play(source)
            
    async def generate_radio(self, track: Track | None):
        if track:
            return await self.music.recommendation.generate_radio_from_track(track)