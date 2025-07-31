"""
Phoneme Manager Module
Static class that handles loading and precompiling phonemes into phoneme_patterns_cache
that is then retrievable by TTS components. The manager's phoneme_patterns_cache is 
initialized on demand when phoneme_patterns_cache with a given phoneme_cache_id getter is called.
"""

import logging
import re
import hashlib
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from src.requests_handler import get as cached_get

logger = logging.getLogger(__name__)

@dataclass
class TtsPhoneme:
    """Represents a phoneme mapping for TTS"""
    name: str
    phoneme: Optional[str] = None
    sub: Optional[str] = None

class PhonemeManager:
    """
    Static class that manages phoneme loading and pattern compilation with caching
    """
    
    # Class-level cache for phoneme patterns by phoneme cache ID
    _phoneme_patterns_cache: Dict[str, Dict[str, List[Tuple]]] = {}
    _phoneme_data_cache: Dict[str, List[TtsPhoneme]] = {}
    _loading_locks: Dict[str, asyncio.Lock] = {}
    
    @classmethod
    def _generate_phoneme_cache_id(cls, azure_config) -> str:
        """
        Generate a unique phoneme cache ID based on Azure TTS configuration
        
        Args:
            azure_config: Azure TTS configuration object
            
        Returns:
            Unique string identifier for this configuration's phoneme cache
        """
        # Create a hash based on the configuration URLs and models
        config_data = []
        
        # Add global phoneme URL if available
        if hasattr(azure_config, 'phonemeUrl') and azure_config.phonemeUrl:
            config_data.append(f"global:{azure_config.phonemeUrl}")
        
        # Add lexicon URL if available
        if hasattr(azure_config, 'lexiconURL') and azure_config.lexiconURL:
            config_data.append(f"lexicon:{azure_config.lexiconURL}")
        
        # Add model-specific phoneme URLs
        if hasattr(azure_config, 'models') and azure_config.models:
            for model in azure_config.models:
                if hasattr(model, 'phonemeUrl') and model.phonemeUrl:
                    config_data.append(f"model:{model.language}:{model.phonemeUrl}")
        
        # Create hash from the configuration data
        config_string = "|".join(sorted(config_data))
        phoneme_cache_id = hashlib.md5(config_string.encode()).hexdigest()
        
        logger.debug(f"Generated phoneme cache ID: {phoneme_cache_id} for config: {config_string}")
        return phoneme_cache_id
    
    @classmethod
    async def get_phoneme_patterns_cache(cls, azure_config) -> Dict[str, List[Tuple]]:
        """
        Get phoneme patterns cache for a given Azure TTS configuration.
        Initializes cache on demand if not already loaded.
        
        Args:
            azure_config: Azure TTS configuration object
            
        Returns:
            Dictionary mapping language codes to compiled phoneme patterns
        """
        phoneme_cache_id = cls._generate_phoneme_cache_id(azure_config)
        
        # Return cached patterns if already loaded
        if phoneme_cache_id in cls._phoneme_patterns_cache:
            logger.debug(f"Returning cached phoneme patterns for phoneme cache ID: {phoneme_cache_id}")
            return cls._phoneme_patterns_cache[phoneme_cache_id]
        
        # Use a lock to prevent concurrent loading of the same config
        if phoneme_cache_id not in cls._loading_locks:
            cls._loading_locks[phoneme_cache_id] = asyncio.Lock()
        
        async with cls._loading_locks[phoneme_cache_id]:
            # Double-check after acquiring lock
            if phoneme_cache_id in cls._phoneme_patterns_cache:
                return cls._phoneme_patterns_cache[phoneme_cache_id]
            
            logger.info(f"Loading phoneme patterns for phoneme cache ID: {phoneme_cache_id}")
            
            # Load and compile phoneme patterns
            patterns_cache = await cls._load_and_compile_phonemes(azure_config)
            cls._phoneme_patterns_cache[phoneme_cache_id] = patterns_cache
            
            logger.info(f"Cached phoneme patterns for {len(patterns_cache)} languages under phoneme cache ID: {phoneme_cache_id}")
            return patterns_cache
    
    @classmethod
    async def _load_and_compile_phonemes(cls, azure_config) -> Dict[str, List[Tuple]]:
        """
        Load phoneme data from URLs and compile patterns for all languages
        
        Args:
            azure_config: Azure TTS configuration object
            
        Returns:
            Dictionary mapping language codes to compiled phoneme patterns
        """
        global_phonemes: List[TtsPhoneme] = []
        localized_phonemes: Dict[str, List[TtsPhoneme]] = {}
        
        try:
            start_time = asyncio.get_event_loop().time()
            # Load global phonemes if available
            if hasattr(azure_config, 'phonemeUrl') and azure_config.phonemeUrl:
                global_phonemes = await cls._load_phoneme_data(azure_config.phonemeUrl)
                logger.info(f"Loaded {len(global_phonemes)} global phonemes")
            
            # Load localized phonemes for each model
            if hasattr(azure_config, 'models') and azure_config.models:
                for model in azure_config.models:
                    if hasattr(model, 'phonemeUrl') and model.phonemeUrl:
                        lang_phonemes = await cls._load_phoneme_data(model.phonemeUrl)
                        if lang_phonemes:
                            localized_phonemes[model.language.lower()] = lang_phonemes
                            logger.info(f"Loaded {len(lang_phonemes)} phonemes for {model.language}")
            
            # Compile patterns for all languages
            patterns_cache = cls._compile_all_patterns(global_phonemes, localized_phonemes)
            logger.info(f"Compiled phoneme patterns for {len(patterns_cache)} languages in {asyncio.get_event_loop().time() - start_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Failed to load and compile phonemes: {str(e)}")
            patterns_cache = {}
        
        return patterns_cache
    
    @classmethod
    async def _load_phoneme_data(cls, url: str) -> List[TtsPhoneme]:
        """
        Load phoneme data from a URL using cached requests
        
        Args:
            url: URL to load phoneme data from
            
        Returns:
            List of TtsPhoneme objects
        """
        # Check if already cached
        if url in cls._phoneme_data_cache:
            logger.debug(f"Returning cached phoneme data for URL: {url}")
            return cls._phoneme_data_cache[url]
        
        try:
            logger.info(f"Loading phoneme data from: {url}")
            
            # Use cached requests handler for better performance and caching
            response = await cached_get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                phonemes = []
                for item in data:
                    if isinstance(item, dict) and 'name' in item:
                        phoneme = TtsPhoneme(
                            name=item['name'],
                            phoneme=item.get('phoneme'),
                            sub=item.get('sub')
                        )
                        # Only add if it has either phoneme or sub
                        if phoneme.phoneme or phoneme.sub:
                            phonemes.append(phoneme)
                
                logger.info(f"Successfully loaded {len(phonemes)} phonemes from {url}")
                cls._phoneme_data_cache[url] = phonemes
                return phonemes
            else:
                logger.error(f"Failed to load phonemes from {url}: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error loading phonemes from {url}: {str(e)}")
        
        return []
    
    @classmethod
    def _compile_all_patterns(cls, global_phonemes: List[TtsPhoneme], 
                            localized_phonemes: Dict[str, List[TtsPhoneme]]) -> Dict[str, List[Tuple]]:
        """
        Compile regex patterns for all languages
        
        Args:
            global_phonemes: List of global phonemes
            localized_phonemes: Dictionary of localized phonemes by language
            
        Returns:
            Dictionary mapping language codes to compiled phoneme patterns
        """
        patterns_cache = {}
        
        # Get all languages that have localized phonemes
        all_languages = set(localized_phonemes.keys())
        
        # Also create a default pattern set for languages without specific phonemes
        for language in all_languages.union({'default'}):
            patterns_cache[language] = cls._compile_patterns_for_language(
                language, global_phonemes, localized_phonemes
            )
        
        return patterns_cache
    
    @classmethod
    def _compile_patterns_for_language(cls, language: str, global_phonemes: List[TtsPhoneme],
                                     localized_phonemes: Dict[str, List[TtsPhoneme]]) -> List[Tuple]:
        """
        Compile regex patterns for a specific language
        
        Args:
            language: Language code or 'default'
            global_phonemes: List of global phonemes
            localized_phonemes: Dictionary of localized phonemes by language
            
        Returns:
            List of tuples containing (compiled_pattern, replacement_tag, name_key)
        """
        if language == 'default':
            localized = []
        else:
            localized = localized_phonemes.get(language, [])
        
        # Create phoneme map (prioritize localized over global)
        phoneme_map = {}
        
        # Add global phonemes first
        for phoneme in global_phonemes:
            if phoneme.name and (phoneme.sub or phoneme.phoneme):
                phoneme_map[phoneme.name] = phoneme
        
        # Add localized phonemes (will override global ones with same name)
        for phoneme in localized:
            if phoneme.name and (phoneme.sub or phoneme.phoneme):
                phoneme_map[phoneme.name] = phoneme
        
        if not phoneme_map:
            return []
        
        # Sort names by length (longest first) and compile patterns
        sorted_names = sorted(phoneme_map.keys(), key=len, reverse=True)
        patterns_and_replacements = []
        
        for name_key in sorted_names:
            phoneme_item = phoneme_map[name_key]
            
            # Create replacement tag
            if phoneme_item.sub:
                replacement_tag = f'<sub alias="{phoneme_item.sub}">{name_key}</sub>'
            else:
                replacement_tag = f'<phoneme alphabet="ipa" ph="{phoneme_item.phoneme}">{name_key}</phoneme>'
            
            # Pre-compile regex pattern
            escaped_name = re.escape(name_key)
            pattern = re.compile(rf'(<(?:phoneme|sub)\b[^>]*>.*?</(?:phoneme|sub)>)|(\b{escaped_name}\b)', 
                               flags=re.IGNORECASE | re.DOTALL)
            
            patterns_and_replacements.append((pattern, replacement_tag, name_key))
        
        logger.debug(f"Compiled {len(patterns_and_replacements)} phoneme patterns for language: {language}")
        return patterns_and_replacements
    
    @classmethod
    def clear_cache(cls, phoneme_cache_id: Optional[str] = None) -> None:
        """
        Clear phoneme cache for a specific phoneme cache ID or all configs
        
        Args:
            phoneme_cache_id: Specific phoneme cache ID to clear, or None to clear all
        """
        if phoneme_cache_id:
            cls._phoneme_patterns_cache.pop(phoneme_cache_id, None)
            logger.info(f"Cleared phoneme cache for phoneme cache ID: {phoneme_cache_id}")
        else:
            cls._phoneme_patterns_cache.clear()
            cls._phoneme_data_cache.clear()
            cls._loading_locks.clear()
            logger.info("Cleared all phoneme caches")
    
    @classmethod
    def get_cache_stats(cls) -> Dict[str, int]:
        """
        Get statistics about the current cache state
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "phoneme_cache_configs": len(cls._phoneme_patterns_cache),
            "phoneme_data_caches": len(cls._phoneme_data_cache),
            "active_locks": len(cls._loading_locks)
        }
