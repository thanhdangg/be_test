"""
Parser Module for Access Process Backend
Parses incoming TAG data and extracts tag_id, cnt, and timestamp
Format: TAG,<tag_id>,<cnt>,<timestamp>
Example: TAG,fa451f0755d8,197,20251003140059.456
"""

import re
import logging
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TagData:
    """Data class for parsed tag information"""
    tag_id: str
    cnt: int
    timestamp: str
    raw_data: str
    parsed_at: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "tag_id": self.tag_id,
            "cnt": self.cnt,
            "timestamp": self.timestamp,
            "raw_data": self.raw_data,
            "parsed_at": self.parsed_at
        }
    
    def __str__(self) -> str:
        return f"TagData(id={self.tag_id}, cnt={self.cnt}, ts={self.timestamp})"


class TagParser:
    """Parser for TAG data format"""
    
    # Regex pattern for TAG format: TAG,<tag_id>,<cnt>,<timestamp>
    TAG_PATTERN = re.compile(
        r'^TAG,([a-fA-F0-9]+),(\d+),(\d{14}\.\d{3})$'
    )
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize parser
        
        Args:
            strict_mode: If True, enforce strict format validation
        """
        self.strict_mode = strict_mode
        self.stats = {
            "total_parsed": 0,
            "successful_parses": 0,
            "failed_parses": 0,
            "validation_errors": 0
        }
    
    def parse_tag_data(self, raw_data: str) -> Optional[TagData]:
        """
        Parse TAG data string
        
        Args:
            raw_data: Raw TAG data string
            
        Returns:
            TagData object if parsing successful, None otherwise
        """
        raw_data = raw_data.strip()
        self.stats["total_parsed"] += 1
        
        try:
            # Try strict pattern first
            match = self.TAG_PATTERN.match(raw_data)
            
            if not match:
                logger.warning(f"Invalid TAG format: {raw_data}")
                self.stats["failed_parses"] += 1
                return None
            
            tag_id, cnt_str, timestamp = match.groups()
            
            # Validate and convert CNT
            try:
                cnt = int(cnt_str)
                if cnt < 0:
                    raise ValueError("CNT cannot be negative")
            except ValueError as e:
                logger.error(f"Invalid CNT value '{cnt_str}': {e}")
                self.stats["validation_errors"] += 1
                return None
            
            # Validate tag_id
            if not self._validate_tag_id(tag_id):
                logger.error(f"Invalid tag_id format: {tag_id}")
                self.stats["validation_errors"] += 1
                return None
            
            # Validate timestamp
            if self.strict_mode and not self._validate_timestamp(timestamp):
                logger.error(f"Invalid timestamp format: {timestamp}")
                self.stats["validation_errors"] += 1
                return None
            
            parsed_at = datetime.now().isoformat()
            
            tag_data = TagData(
                tag_id=tag_id,
                cnt=cnt,
                timestamp=timestamp,
                raw_data=raw_data,
                parsed_at=parsed_at
            )
            
            self.stats["successful_parses"] += 1
            logger.debug(f"Successfully parsed: {tag_data}")
            
            return tag_data
            
        except Exception as e:
            logger.error(f"Error parsing TAG data '{raw_data}': {e}")
            self.stats["failed_parses"] += 1
            return None
    
    def _validate_tag_id(self, tag_id: str) -> bool:
        if not tag_id:
            return False
        
        if self.strict_mode:
            # Strict mode: only hexadecimal characters, 8-16 chars
            return bool(re.match(r'^[a-fA-F0-9]{8,16}$', tag_id))
        else:
            # Flexible mode: alphanumeric, 4-32 chars
            return bool(re.match(r'^[a-zA-Z0-9]{4,32}$', tag_id))
    
    def _validate_timestamp(self, timestamp: str) -> bool:
        if not timestamp:
            return False
        
        if self.strict_mode:
            # Strict format: YYYYMMDDHHMMSS.mmm
            try:
                if not re.match(r'^\d{14}\.\d{3}$', timestamp):
                    return False
                
                # Parse to validate date
                date_part = timestamp[:14]
                datetime.strptime(date_part, "%Y%m%d%H%M%S")
                return True
                
            except ValueError:
                return False
        else:
            return len(timestamp.strip()) > 0
    
    def parse_batch(self, data_lines: list) -> Tuple[list, list]:
        """
        Parse multiple TAG data lines
        
        Args:
            data_lines: List of raw TAG data strings
            
        Returns:
            Tuple of (successful_parses, failed_lines)
        """
        successful = []
        failed = []
        
        for line in data_lines:
            parsed = self.parse_tag_data(line)
            if parsed:
                successful.append(parsed)
            else:
                failed.append(line)
        
        logger.info(f"Batch parse: {len(successful)} success, {len(failed)} failed")
        return successful, failed
    
    def get_stats(self) -> Dict:
        """Get parser statistics"""
        stats = self.stats.copy()
        if stats["total_parsed"] > 0:
            stats["success_rate"] = stats["successful_parses"] / stats["total_parsed"]
        else:
            stats["success_rate"] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset parser statistics"""
        self.stats = {
            "total_parsed": 0,
            "successful_parses": 0,
            "failed_parses": 0,
            "validation_errors": 0
        }
        logger.info("Parser statistics reset")



def create_parser(strict_mode: bool = True) -> TagParser:
    return TagParser(strict_mode=strict_mode)


if __name__ == "__main__":
    # Test the parser module
    print("Testing TAG Parser...")
    
    parser = TagParser(strict_mode=True)
    
    # Test data
    test_cases = [
        "TAG,fa451f0755d8,197,20251003140059.456",  # Valid
        "TAG,ab123c4567ef,42,20251003140105.123",   # Valid
        "TAG,fa451f0755d8,198,20251003140120.456",  # Valid (CNT increment)
        "TAG,invalid_tag,199,20251003140125.456",   # Invalid tag_id (underscore)
        "TAG,fa451f0755d8,-1,20251003140130.456",   # Invalid CNT (negative)
        "TAG,fa451f0755d8,200,invalid_timestamp",   # Invalid timestamp
        "INVALID,fa451f0755d8,201,20251003140135.456",  # Invalid prefix
        "",  # Empty string
        "TAG,fa451f0755d8,202",  # Missing timestamp
    ]
    
    print("Parsing test cases:")
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. Input: '{test_case}'")
        result = parser.parse_tag_data(test_case)
        if result:
            print(f"   Success: {result}")
        else:
            print(f"   Failed to parse")
    
    print("\nParser Statistics:")
    stats = parser.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test flexible mode
    print("\n\nTesting flexible mode:")
    flexible_parser = TagParser(strict_mode=False)
    
    flexible_cases = [
        "TAG,MyTag123,100,2024-05-03T14:00:59.456Z",
        "TAG,sensor_01,200,custom_timestamp_format",
    ]
    
    for case in flexible_cases:
        print(f"Input: '{case}'")
        result = flexible_parser.parse_tag_data(case)
        if result:
            print(f"  Success: {result}")
        else:
            print(f"  Failed")
