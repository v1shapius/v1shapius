from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Text, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum
from datetime import datetime, timedelta
import hashlib
import json

class SecurityEventType(enum.Enum):
    """Security event type enumeration"""
    SUSPICIOUS_MATCH = "suspicious_match"
    RATING_SPIKE = "rating_spike"
    MULTIPLE_ACCOUNTS = "multiple_accounts"
    UNUSUAL_ACTIVITY = "unusual_activity"
    REFEREE_ABUSE = "referee_abuse"
    SYSTEM_ABUSE = "system_abuse"

class SecurityLevel(enum.Enum):
    """Security level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SecurityEvent(Base, TimestampMixin):
    """Security event model for tracking suspicious activities"""
    
    __tablename__ = "security_events"
    
    id = Column(Integer, primary_key=True)
    event_type = Column(Enum(SecurityEventType), nullable=False)
    security_level = Column(Enum(SecurityLevel), nullable=False)
    
    # Event details
    guild_id = Column(BigInteger, nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)
    
    # Event data
    description = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=True)  # Structured evidence data
    risk_score = Column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    
    # Status
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_by = Column(BigInteger, nullable=True)  # Discord ID of admin who resolved
    resolution_notes = Column(Text, nullable=True)
    resolution_time = Column(DateTime, nullable=True)
    
    # Relationships
    player = relationship("Player", back_populates="security_events")
    match = relationship("Match", back_populates="security_events")
    
    def __repr__(self):
        return f"<SecurityEvent(id={self.id}, type={self.event_type.value}, level={self.security_level.value})>"
    
    def resolve(self, admin_id: int, notes: str = None):
        """Resolve the security event"""
        self.is_resolved = True
        self.resolved_by = admin_id
        self.resolution_notes = notes
        self.resolution_time = datetime.utcnow()
    
    @property
    def is_high_risk(self) -> bool:
        """Check if event is high risk"""
        return self.risk_score >= 0.7 or self.security_level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]

class PlayerSecurityProfile(Base, TimestampMixin):
    """Player security profile for tracking behavior patterns"""
    
    __tablename__ = "player_security_profiles"
    
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, unique=True)
    
    # Risk assessment
    overall_risk_score = Column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    risk_level = Column(Enum(SecurityLevel), default=SecurityLevel.LOW, nullable=False)
    
    # Behavior tracking
    total_matches = Column(Integer, default=0, nullable=False)
    suspicious_matches = Column(Integer, default=0, nullable=False)
    rating_changes = Column(JSON, nullable=True)  # Track rating changes over time
    
    # Account security
    ip_addresses = Column(JSON, nullable=True)  # Track IP addresses used
    device_fingerprints = Column(JSON, nullable=True)  # Track device fingerprints
    last_suspicious_activity = Column(DateTime, nullable=True)
    
    # Restrictions
    is_restricted = Column(Boolean, default=False, nullable=False)
    restriction_reason = Column(Text, nullable=True)
    restriction_until = Column(DateTime, nullable=True)
    
    # Relationships
    player = relationship("Player", back_populates="security_profile")
    
    def __repr__(self):
        return f"<PlayerSecurityProfile(player_id={self.player_id}, risk_score={self.overall_risk_score})>"
    
    @property
    def is_restricted_now(self) -> bool:
        """Check if player is currently restricted"""
        if not self.is_restricted:
            return False
        
        if self.restriction_until is None:
            return True
        
        return datetime.utcnow() <= self.restriction_until
    
    def update_risk_score(self, new_score: float):
        """Update overall risk score"""
        self.overall_risk_score = max(0.0, min(1.0, new_score))
        
        # Update risk level based on score
        if self.overall_risk_score >= 0.8:
            self.risk_level = SecurityLevel.CRITICAL
        elif self.overall_risk_score >= 0.6:
            self.risk_level = SecurityLevel.HIGH
        elif self.overall_risk_score >= 0.3:
            self.risk_level = SecurityLevel.MEDIUM
        else:
            self.risk_level = SecurityLevel.LOW
    
    def add_suspicious_match(self):
        """Increment suspicious match count"""
        self.suspicious_matches += 1
        self.last_suspicious_activity = datetime.utcnow()
        
        # Recalculate risk score
        suspicious_ratio = self.suspicious_matches / max(1, self.total_matches)
        self.update_risk_score(suspicious_ratio)
    
    def add_rating_change(self, old_rating: int, new_rating: int, match_id: int):
        """Track rating change for analysis"""
        if self.rating_changes is None:
            self.rating_changes = []
        
        change_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "old_rating": old_rating,
            "new_rating": new_rating,
            "change": new_rating - old_rating,
            "match_id": match_id
        }
        
        self.rating_changes.append(change_data)
        
        # Keep only last 100 changes
        if len(self.rating_changes) > 100:
            self.rating_changes = self.rating_changes[-100:]
    
    def restrict_player(self, reason: str, duration_days: int = 7):
        """Restrict player for specified duration"""
        self.is_restricted = True
        self.restriction_reason = reason
        self.restriction_until = datetime.utcnow() + timedelta(days=duration_days)
    
    def lift_restriction(self):
        """Lift player restriction"""
        self.is_restricted = False
        self.restriction_reason = None
        self.restriction_until = None

class MatchIntegrityCheck(Base, TimestampMixin):
    """Match integrity check for verifying match results"""
    
    __tablename__ = "match_integrity_checks"
    
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, unique=True)
    
    # Integrity metrics
    time_consistency_score = Column(Float, default=1.0, nullable=False)  # 0.0 to 1.0
    result_plausibility_score = Column(Float, default=1.0, nullable=False)  # 0.0 to 1.0
    overall_integrity_score = Column(Float, default=1.0, nullable=False)  # 0.0 to 1.0
    
    # Check details
    performed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    check_type = Column(String(50), nullable=False)  # automatic, manual, triggered
    details = Column(JSON, nullable=True)  # Detailed check results
    
    # Flags
    is_suspicious = Column(Boolean, default=False, nullable=False)
    requires_review = Column(Boolean, default=False, nullable=False)
    reviewed_by = Column(BigInteger, nullable=True)  # Discord ID of reviewer
    review_notes = Column(Text, nullable=True)
    
    # Relationships
    match = relationship("Match", back_populates="integrity_check")
    
    def __repr__(self):
        return f"<MatchIntegrityCheck(match_id={self.match_id}, integrity_score={self.overall_integrity_score})>"
    
    def calculate_integrity_score(self):
        """Calculate overall integrity score"""
        # Weighted average of individual scores
        self.overall_integrity_score = (
            self.time_consistency_score * 0.4 +
            self.result_plausibility_score * 0.6
        )
        
        # Determine if suspicious
        self.is_suspicious = self.overall_integrity_score < 0.7
        self.requires_review = self.overall_integrity_score < 0.8
    
    def flag_for_review(self, reason: str):
        """Flag match for manual review"""
        self.requires_review = True
        self.review_notes = reason
    
    def mark_reviewed(self, reviewer_id: int, notes: str = None):
        """Mark as reviewed by admin"""
        self.reviewed_by = reviewer_id
        if notes:
            self.review_notes = notes
        self.requires_review = False

class SecurityRule(Base, TimestampMixin):
    """Security rule for automated detection"""
    
    __tablename__ = "security_rules"
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    
    # Rule configuration
    rule_name = Column(String(100), nullable=False)
    rule_type = Column(String(50), nullable=False)  # rating_spike, match_pattern, etc.
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Rule parameters
    parameters = Column(JSON, nullable=False)  # Rule-specific parameters
    threshold = Column(Float, nullable=False)  # Trigger threshold
    
    # Actions
    actions = Column(JSON, nullable=False)  # Actions to take when triggered
    notification_channels = Column(JSON, nullable=True)  # Channels to notify
    
    # Statistics
    times_triggered = Column(Integer, default=0, nullable=False)
    last_triggered = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<SecurityRule(id={self.id}, name='{self.rule_name}', type={self.rule_type})>"
    
    def should_trigger(self, value: float) -> bool:
        """Check if rule should trigger based on value"""
        return value >= self.threshold
    
    def trigger(self):
        """Mark rule as triggered"""
        self.times_triggered += 1
        self.last_triggered = datetime.utcnow()
    
    def get_action_commands(self) -> list:
        """Get list of action commands to execute"""
        if not self.actions:
            return []
        return self.actions.get("commands", [])
    
    def get_notification_channels(self) -> list:
        """Get list of channels to notify"""
        if not self.notification_channels:
            return []
        return self.notification_channels.get("channels", [])