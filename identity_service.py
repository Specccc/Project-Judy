import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from config import (
    DATABASE_FOLDER,
    IDENTITY_DATABASE_FILE,
    PROFILE_MAX_PREFERRED_NAME_LENGTH,
    RELATIONSHIP_SCORE_MAXIMUM,
    RELATIONSHIP_SCORE_MINIMUM,
)


_database_lock = Lock()

_POSITIVE_MARKERS = {
    "appreciate",
    "awesome",
    "good",
    "great",
    "helpful",
    "love",
    "nice",
    "please",
    "preem",
    "thanks",
    "thank",
}

_HOSTILE_MARKERS = {
    "hate you",
    "idiot",
    "moron",
    "shut up",
    "stupid",
    "trash",
    "useless",
}


@dataclass(frozen=True)
class UserProfile:
    guild_id: int
    user_id: int
    preferred_name: str | None
    display_name: str
    first_seen_at: str
    last_seen_at: str
    message_count: int


@dataclass(frozen=True)
class Relationship:
    guild_id: int
    user_id: int
    trust: int
    familiarity: int
    affinity: int
    interaction_count: int
    tier: str
    last_interaction_at: str | None


def _now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def _clean_name(value):
    return " ".join(
        str(value).split()
    )[
        :PROFILE_MAX_PREFERRED_NAME_LENGTH
    ]


def _clamp(value):
    return max(
        RELATIONSHIP_SCORE_MINIMUM,
        min(
            RELATIONSHIP_SCORE_MAXIMUM,
            int(value)
        )
    )


def relationship_tier(
    trust,
    familiarity,
    affinity
):
    trust = int(trust)
    familiarity = int(familiarity)
    affinity = int(affinity)

    if trust >= 50 and familiarity >= 80 and affinity >= 35:
        return "close"

    if trust >= 25 and familiarity >= 40 and affinity >= 15:
        return "trusted"

    if trust >= 10 and familiarity >= 15 and affinity >= 5:
        return "choom"

    if familiarity >= 3:
        return "acquaintance"

    return "stranger"


def initialize_identity_database():
    DATABASE_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    with _database_lock:
        with sqlite3.connect(
            IDENTITY_DATABASE_FILE,
            timeout=10
        ) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    preferred_name TEXT,
                    display_name TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    message_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS relationships (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    trust INTEGER NOT NULL DEFAULT 0,
                    familiarity INTEGER NOT NULL DEFAULT 0,
                    affinity INTEGER NOT NULL DEFAULT 0,
                    interaction_count INTEGER NOT NULL DEFAULT 0,
                    last_interaction_at TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_profiles_last_seen
                ON user_profiles(last_seen_at)
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_relationships_tier_scores
                ON relationships(
                    familiarity,
                    trust,
                    affinity
                )
                """
            )

            connection.commit()


def _profile_from_row(row):
    if row is None:
        return None

    return UserProfile(
        guild_id=int(row[0]),
        user_id=int(row[1]),
        preferred_name=row[2],
        display_name=row[3],
        first_seen_at=row[4],
        last_seen_at=row[5],
        message_count=int(row[6]),
    )


def _relationship_from_row(row):
    if row is None:
        return None

    trust = int(row[2])
    familiarity = int(row[3])
    affinity = int(row[4])

    return Relationship(
        guild_id=int(row[0]),
        user_id=int(row[1]),
        trust=trust,
        familiarity=familiarity,
        affinity=affinity,
        interaction_count=int(row[5]),
        tier=relationship_tier(
            trust,
            familiarity,
            affinity
        ),
        last_interaction_at=row[6],
    )


def get_profile(
    guild_id,
    user_id
):
    initialize_identity_database()

    with _database_lock:
        with sqlite3.connect(
            IDENTITY_DATABASE_FILE,
            timeout=10
        ) as connection:
            row = connection.execute(
                """
                SELECT
                    guild_id,
                    user_id,
                    preferred_name,
                    display_name,
                    first_seen_at,
                    last_seen_at,
                    message_count
                FROM user_profiles
                WHERE guild_id = ?
                AND user_id = ?
                """,
                (
                    int(guild_id),
                    int(user_id)
                )
            ).fetchone()

    return _profile_from_row(row)


def get_relationship(
    guild_id,
    user_id
):
    initialize_identity_database()

    with _database_lock:
        with sqlite3.connect(
            IDENTITY_DATABASE_FILE,
            timeout=10
        ) as connection:
            row = connection.execute(
                """
                SELECT
                    guild_id,
                    user_id,
                    trust,
                    familiarity,
                    affinity,
                    interaction_count,
                    last_interaction_at
                FROM relationships
                WHERE guild_id = ?
                AND user_id = ?
                """,
                (
                    int(guild_id),
                    int(user_id)
                )
            ).fetchone()

    return _relationship_from_row(row)


def set_preferred_name(
    guild_id,
    user_id,
    display_name,
    preferred_name
):
    initialize_identity_database()

    preferred_name = _clean_name(
        preferred_name
    )

    if (
        not preferred_name
        or len(preferred_name)
        > PROFILE_MAX_PREFERRED_NAME_LENGTH
    ):
        return False

    now = _now()

    with _database_lock:
        with sqlite3.connect(
            IDENTITY_DATABASE_FILE,
            timeout=10
        ) as connection:
            connection.execute(
                """
                INSERT INTO user_profiles (
                    guild_id,
                    user_id,
                    preferred_name,
                    display_name,
                    first_seen_at,
                    last_seen_at,
                    message_count,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                ON CONFLICT(guild_id, user_id)
                DO UPDATE SET
                    preferred_name = excluded.preferred_name,
                    display_name = excluded.display_name,
                    updated_at = excluded.updated_at
                """,
                (
                    int(guild_id),
                    int(user_id),
                    preferred_name,
                    _clean_name(
                        display_name
                    ) or "Unknown user",
                    now,
                    now,
                    now
                )
            )

            connection.commit()

    return True


def clear_preferred_name(
    guild_id,
    user_id
):
    initialize_identity_database()

    with _database_lock:
        with sqlite3.connect(
            IDENTITY_DATABASE_FILE,
            timeout=10
        ) as connection:
            cursor = connection.execute(
                """
                UPDATE user_profiles
                SET preferred_name = NULL,
                    updated_at = ?
                WHERE guild_id = ?
                AND user_id = ?
                """,
                (
                    _now(),
                    int(guild_id),
                    int(user_id)
                )
            )

            connection.commit()

    return cursor.rowcount > 0


def _relationship_deltas(
    message,
    interaction_count
):
    normalized = str(
        message
    ).casefold()

    positive = any(
        marker in normalized
        for marker in _POSITIVE_MARKERS
    )

    hostile = any(
        marker in normalized
        for marker in _HOSTILE_MARKERS
    )

    familiarity_delta = 1
    trust_delta = 0
    affinity_delta = 0

    if hostile:
        trust_delta = -2
        affinity_delta = -3
    elif positive:
        affinity_delta = 1

    if (
        not hostile
        and interaction_count % 5 == 0
    ):
        trust_delta += 1

    return (
        trust_delta,
        familiarity_delta,
        affinity_delta
    )


def record_interaction(
    guild_id,
    user_id,
    display_name,
    message
):
    initialize_identity_database()

    guild_id = int(guild_id)
    user_id = int(user_id)
    display_name = _clean_name(
        display_name
    ) or "Unknown user"
    now = _now()

    with _database_lock:
        with sqlite3.connect(
            IDENTITY_DATABASE_FILE,
            timeout=10
        ) as connection:
            connection.execute(
                """
                INSERT INTO user_profiles (
                    guild_id,
                    user_id,
                    preferred_name,
                    display_name,
                    first_seen_at,
                    last_seen_at,
                    message_count,
                    updated_at
                )
                VALUES (?, ?, NULL, ?, ?, ?, 1, ?)
                ON CONFLICT(guild_id, user_id)
                DO UPDATE SET
                    display_name = excluded.display_name,
                    last_seen_at = excluded.last_seen_at,
                    message_count = message_count + 1,
                    updated_at = excluded.updated_at
                """,
                (
                    guild_id,
                    user_id,
                    display_name,
                    now,
                    now,
                    now
                )
            )

            relationship_row = connection.execute(
                """
                SELECT
                    trust,
                    familiarity,
                    affinity,
                    interaction_count
                FROM relationships
                WHERE guild_id = ?
                AND user_id = ?
                """,
                (
                    guild_id,
                    user_id
                )
            ).fetchone()

            if relationship_row is None:
                trust = 0
                familiarity = 0
                affinity = 0
                interaction_count = 0
            else:
                (
                    trust,
                    familiarity,
                    affinity,
                    interaction_count
                ) = relationship_row

            interaction_count += 1

            (
                trust_delta,
                familiarity_delta,
                affinity_delta
            ) = _relationship_deltas(
                message,
                interaction_count
            )

            trust = _clamp(
                trust + trust_delta
            )
            familiarity = _clamp(
                familiarity
                + familiarity_delta
            )
            affinity = _clamp(
                affinity + affinity_delta
            )

            connection.execute(
                """
                INSERT INTO relationships (
                    guild_id,
                    user_id,
                    trust,
                    familiarity,
                    affinity,
                    interaction_count,
                    last_interaction_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, user_id)
                DO UPDATE SET
                    trust = excluded.trust,
                    familiarity = excluded.familiarity,
                    affinity = excluded.affinity,
                    interaction_count = excluded.interaction_count,
                    last_interaction_at = excluded.last_interaction_at,
                    updated_at = excluded.updated_at
                """,
                (
                    guild_id,
                    user_id,
                    trust,
                    familiarity,
                    affinity,
                    interaction_count,
                    now,
                    now
                )
            )

            connection.commit()

    return (
        get_profile(
            guild_id,
            user_id
        ),
        get_relationship(
            guild_id,
            user_id
        )
    )


def build_identity_context(
    guild_id,
    user_id
):
    profile = get_profile(
        guild_id,
        user_id
    )

    relationship = get_relationship(
        guild_id,
        user_id
    )

    if profile is None:
        return (
            "No established user profile. "
            "Treat this person as a stranger."
        )

    resolved_name = (
        profile.preferred_name
        or profile.display_name
    )

    lines = [
        f"Preferred name: {resolved_name}",
        (
            "Observed Discord display name: "
            f"{profile.display_name}"
        ),
        f"Direct interactions: {profile.message_count}",
    ]

    if relationship is not None:
        lines.extend([
            (
                "Relationship tier: "
                f"{relationship.tier}"
            ),
            f"Trust score: {relationship.trust}",
            (
                "Familiarity score: "
                f"{relationship.familiarity}"
            ),
            f"Affinity score: {relationship.affinity}",
        ])

    lines.append(
        "Use this state subtly. Never quote scores, "
        "tiers, or internal metadata to the user."
    )

    return "\n".join(lines)


def delete_user_identity(
    guild_id,
    user_id
):
    initialize_identity_database()

    deleted_rows = 0

    with _database_lock:
        with sqlite3.connect(
            IDENTITY_DATABASE_FILE,
            timeout=10
        ) as connection:
            for table_name in (
                "user_profiles",
                "relationships"
            ):
                cursor = connection.execute(
                    f"DELETE FROM {table_name} "
                    "WHERE guild_id = ? "
                    "AND user_id = ?",
                    (
                        int(guild_id),
                        int(user_id)
                    )
                )

                deleted_rows += max(
                    cursor.rowcount,
                    0
                )

            connection.commit()

    return deleted_rows


def identity_statistics():
    initialize_identity_database()

    with _database_lock:
        with sqlite3.connect(
            IDENTITY_DATABASE_FILE,
            timeout=10
        ) as connection:
            profiles = connection.execute(
                """
                SELECT COUNT(*)
                FROM user_profiles
                """
            ).fetchone()[0]

            relationships = connection.execute(
                """
                SELECT COUNT(*)
                FROM relationships
                """
            ).fetchone()[0]

            tier_counts = {
                tier: 0
                for tier in (
                    "stranger",
                    "acquaintance",
                    "choom",
                    "trusted",
                    "close"
                )
            }

            rows = connection.execute(
                """
                SELECT trust, familiarity, affinity
                FROM relationships
                """
            ).fetchall()

    for trust, familiarity, affinity in rows:
        tier_counts[
            relationship_tier(
                trust,
                familiarity,
                affinity
            )
        ] += 1

    return {
        "profiles": int(profiles),
        "relationships": int(relationships),
        "tiers": tier_counts,
    }
