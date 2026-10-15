"""FR-001,018,020: typed input, identity and bounded configuration."""
import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator
from zoneinfo import ZoneInfo

def now():
    return datetime.now(timezone.utc)
def today():
    return now().astimezone(ZoneInfo('Asia/Kolkata')).date()

class DomainError(Exception):
    def __init__(self, code, message, status=422, retryable=False):
        self.code, self.message, self.status, self.retryable = code, message, status, retryable

class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=180, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=10, max_length=128)
    acknowledged: bool = False

class Scope(BaseModel):
    symbols: list[str] = Field(default_factory=list, max_length=5)
    start: date = Field(default_factory=lambda: today()-timedelta(days=30))
    end: date = Field(default_factory=today)
    index: str = Field(default='NIFTY 50', max_length=50)
    source: str = Field(default='historical', pattern='^(historical|current)$')
    query: str = Field(default='Market briefing', max_length=2000)
    @model_validator(mode='after')
    def valid(self):
        if self.start > self.end or self.end > today() or (self.end-self.start).days > 1826:
            raise ValueError('Use an ordered historical date window of at most five years')
        self.symbols = [s.strip().upper() for s in self.symbols]
        if len(set(self.symbols)) != len(self.symbols) or any(not re.fullmatch(r'[A-Z0-9&._-]{1,30}', s) for s in self.symbols):
            raise ValueError('Symbols must be unique NSE identifiers')
        return self

class Portfolio(Scope):
    weights: list[Decimal]
    amount: Decimal = Field(default=Decimal('100000'), gt=0, le=Decimal('1000000000'))
    @model_validator(mode='after')
    def weights_valid(self):
        if not self.symbols or len(self.weights)!=len(self.symbols) or any(w<=0 or w>1 for w in self.weights) or sum(self.weights)!=1:
            raise ValueError('Provide one positive fractional weight per symbol summing exactly to 1; no automatic normalization')
        return self

class Settings:
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./marketmind.db')
    secret = os.getenv('JWT_SECRET') or os.urandom(48).hex()
    admins = set(s.strip() for s in os.getenv('ADMIN_EMAILS', '').lower().split(',') if s.strip())
    mock = os.getenv('MCP_MODE', 'live') == 'mock'
    timeout = min(30, max(1, float(os.getenv('MCP_TIMEOUT', '25'))))
    retries = min(2, max(0, int(os.getenv('MCP_RETRIES', '1'))))
    ttl = int(os.getenv('CACHE_TTL', '60'))
    stale_ttl = min(900, max(0, int(os.getenv('STALE_CACHE_SECONDS', '900'))))
    freshness = int(os.getenv('FRESHNESS_SECONDS', '600'))
    retention = int(os.getenv('RETENTION_DAYS', '7'))
    concurrency = min(4, max(1, int(os.getenv('MCP_CONCURRENCY', '2'))))

settings = Settings()
