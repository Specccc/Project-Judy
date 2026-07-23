import json
from threading import RLock

from config import (
    CONVERSATION_MEMORY_FILE,
    JUDY_MEMORY_FILE,
    MEMORY_MAX_CONVERSATION_MESSAGES,
    MEMORY_MAX_FACT_LENGTH,
    MEMORY_MAX_FACTS_PER_USER,
)


_file_lock = RLock()


def _user_memory_key(
    guild_id,
    user_id
):
    return (
        f"{int(guild_id)}:"
        f"{int(user_id)}"
    )


def _load_json(file_path):
    try:
        if not file_path.exists():
            return {}

        content = file_path.read_text(
            encoding="utf-8"
        ).strip()

        if not content:
            return {}

        data = json.loads(content)

        if isinstance(data, dict):
            return data

        return {}

    except (
        json.JSONDecodeError,
        OSError
    ):
        return {}


def _save_json(file_path, data):
    file_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary_file = file_path.with_suffix(
        file_path.suffix + ".tmp"
    )

    temporary_file.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    temporary_file.replace(file_path)


def get_conversation(channel_id):
    with _file_lock:
        conversations = _load_json(
            CONVERSATION_MEMORY_FILE
        )

        history = conversations.get(
            str(channel_id),
            []
        )

        if not isinstance(history, list):
            return []

        return list(history)


def add_conversation_message(
    channel_id,
    role,
    content
):
    channel_key = str(channel_id)
    role = str(role)
    content = str(content).strip()

    if not content:
        return

    with _file_lock:
        conversations = _load_json(
            CONVERSATION_MEMORY_FILE
        )

        history = conversations.get(
            channel_key,
            []
        )

        if not isinstance(history, list):
            history = []

        history.append({
            "role": role,
            "content": content
        })

        conversations[channel_key] = history[
            -MEMORY_MAX_CONVERSATION_MESSAGES:
        ]

        _save_json(
            CONVERSATION_MEMORY_FILE,
            conversations
        )


def clear_conversation(channel_id):
    channel_key = str(channel_id)

    with _file_lock:
        conversations = _load_json(
            CONVERSATION_MEMORY_FILE
        )

        removed = conversations.pop(
            channel_key,
            None
        )

        if removed is not None:
            _save_json(
                CONVERSATION_MEMORY_FILE,
                conversations
            )

        return removed is not None


def build_conversation_context(channel_id):
    history = get_conversation(
        channel_id
    )

    lines = []

    for entry in history:
        if not isinstance(entry, dict):
            continue

        role = entry.get(
            "role",
            "user"
        )

        content = str(
            entry.get(
                "content",
                ""
            )
        ).strip()

        if not content:
            continue

        speaker = (
            "Judy"
            if role == "assistant"
            else "User"
        )

        lines.append(
            f"{speaker}: {content}"
        )

    return "\n".join(lines)


def get_user_memory(
    guild_id,
    user_id
):
    with _file_lock:
        memories = _load_json(
            JUDY_MEMORY_FILE
        )

        user_memory = memories.get(
            _user_memory_key(
                guild_id,
                user_id
            ),
            {}
        )

        if not isinstance(
            user_memory,
            dict
        ):
            return {}

        return dict(user_memory)


def remember_user_fact(
    guild_id,
    user_id,
    key,
    value
):
    user_key = _user_memory_key(
        guild_id,
        user_id
    )

    memory_key = (
        str(key)
        .strip()
        .lower()
        .replace(" ", "_")
    )

    memory_value = str(value).strip()

    if not memory_key:
        return False

    if not memory_value:
        return False

    memory_value = memory_value[
        :MEMORY_MAX_FACT_LENGTH
    ]

    with _file_lock:
        memories = _load_json(
            JUDY_MEMORY_FILE
        )

        user_memory = memories.get(
            user_key,
            {}
        )

        if not isinstance(
            user_memory,
            dict
        ):
            user_memory = {}

        if (
            memory_key not in user_memory
            and len(user_memory)
            >= MEMORY_MAX_FACTS_PER_USER
        ):
            return False

        user_memory[memory_key] = (
            memory_value
        )

        memories[user_key] = (
            user_memory
        )

        _save_json(
            JUDY_MEMORY_FILE,
            memories
        )

    return True


def forget_user_fact(
    guild_id,
    user_id,
    key
):
    user_key = _user_memory_key(
        guild_id,
        user_id
    )

    memory_key = (
        str(key)
        .strip()
        .lower()
        .replace(" ", "_")
    )

    with _file_lock:
        memories = _load_json(
            JUDY_MEMORY_FILE
        )

        user_memory = memories.get(
            user_key,
            {}
        )

        if not isinstance(
            user_memory,
            dict
        ):
            return False

        removed = user_memory.pop(
            memory_key,
            None
        )

        if removed is None:
            return False

        if user_memory:
            memories[user_key] = (
                user_memory
            )
        else:
            memories.pop(
                user_key,
                None
            )

        _save_json(
            JUDY_MEMORY_FILE,
            memories
        )

    return True


def forget_user(
    guild_id,
    user_id
):
    user_key = _user_memory_key(
        guild_id,
        user_id
    )

    with _file_lock:
        memories = _load_json(
            JUDY_MEMORY_FILE
        )

        removed = memories.pop(
            user_key,
            None
        )

        if removed is not None:
            _save_json(
                JUDY_MEMORY_FILE,
                memories
            )

        return removed is not None


def forget_guild(guild_id):
    prefix = f"{int(guild_id)}:"

    with _file_lock:
        memories = _load_json(
            JUDY_MEMORY_FILE
        )

        keys_to_remove = [
            key
            for key in memories
            if str(key).startswith(prefix)
        ]

        for key in keys_to_remove:
            memories.pop(key, None)

        if keys_to_remove:
            _save_json(
                JUDY_MEMORY_FILE,
                memories
            )

        return len(keys_to_remove)


def migrate_legacy_user_memories(
    guild_ids
):
    resolved_guild_ids = {
        int(guild_id)
        for guild_id in guild_ids
    }

    if len(resolved_guild_ids) != 1:
        return 0

    guild_id = next(
        iter(resolved_guild_ids)
    )

    with _file_lock:
        memories = _load_json(
            JUDY_MEMORY_FILE
        )

        migrated = 0

        for key in list(memories.keys()):
            key_text = str(key)

            if ":" in key_text:
                continue

            try:
                user_id = int(key_text)
            except ValueError:
                continue

            scoped_key = _user_memory_key(
                guild_id,
                user_id
            )

            if scoped_key not in memories:
                memories[scoped_key] = (
                    memories[key]
                )

            memories.pop(key, None)
            migrated += 1

        if migrated:
            _save_json(
                JUDY_MEMORY_FILE,
                memories
            )

        return migrated


def clear_guild_conversations(
    channel_ids
):
    channel_keys = {
        str(int(channel_id))
        for channel_id in channel_ids
    }

    with _file_lock:
        conversations = _load_json(
            CONVERSATION_MEMORY_FILE
        )

        removed = 0

        for channel_key in channel_keys:
            if conversations.pop(
                channel_key,
                None
            ) is not None:
                removed += 1

        if removed:
            _save_json(
                CONVERSATION_MEMORY_FILE,
                conversations
            )

        return removed


def build_user_memory_context(
    guild_id,
    user_id
):
    user_memory = get_user_memory(
        guild_id,
        user_id
    )

    if not user_memory:
        return (
            "No stored information "
            "about this user."
        )

    lines = []

    for key, value in user_memory.items():
        lines.append(
            f"- {key}: {value}"
        )

    return "\n".join(lines)
