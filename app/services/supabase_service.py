"""
Supabase Authentication & Database Service for SpeakPro AI
Connects to project ymmgezeqdnmpzxvsdtyg.supabase.co using the Supabase Secret Key.
Whenever a user authenticates (sign up or login), this service automatically creates
and syncs their record into Supabase Auth (auth.users) and Supabase database tables.
"""

import os
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("app")

class SupabaseService:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is not None:
            return cls._client
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL", "https://ymmgezeqdnmpzxvsdtyg.supabase.co")
            key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_KEY")
            if url and key:
                cls._client = create_client(url, key)
                return cls._client
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
        return None

    @classmethod
    def sync_user_on_auth(cls, user, action_type="LOGIN"):
        """
        Called whenever authentication happens (user registers or logs in).
        1) Creates user in Supabase Auth (auth.users table) fast without full list scan.
        2) Attempts to record login activity in Supabase public tables.
        """
        sb = cls.get_client()
        if not sb or not user:
            return False

        try:
            # Ensure a clean email address for Supabase Auth
            email = user.email or f"{user.username}@speakpro.ai"
            if "@" not in email:
                email = f"{user.username}@speakpro.ai"

            user_metadata = {
                "display_name": user.username,
                "full_name": user.username,
                "name": user.username,
                "username": user.username,
                "app": "SpeakPro AI Public Speaking Coach",
                "last_auth_action": action_type,
                "last_login": timezone.now().isoformat(),
                "django_user_id": user.id,
            }

            # Fast attempt to create user in Supabase Auth table
            try:
                new_u = sb.auth.admin.create_user({
                    "email": email,
                    "password": "SpeakProUser2026!",
                    "email_confirm": True,
                    "user_metadata": user_metadata,
                })
                logger.info(f"Created new Supabase Auth user: {email}")
            except Exception as e:
                # If already exists or duplicate email, try updating metadata or fallback email
                try:
                    users_list = sb.auth.admin.list_users()
                    for u in users_list:
                        if u.email.lower() == email.lower() or (u.user_metadata and u.user_metadata.get("username") == user.username):
                            sb.auth.admin.update_user_by_id(u.id, {"user_metadata": user_metadata})
                            break
                except Exception as e2:
                    logger.info(f"Supabase Auth update check for {email}: {e2}")

            # Attempt to upsert into public 'user_profiles' table in Supabase (if created by user in SQL Editor)
            try:
                sb.table("user_profiles").upsert({
                    "username": user.username,
                    "email": email,
                    "last_login": timezone.now().isoformat(),
                    "total_sessions": getattr(user, "statistics", None) and user.statistics.total_sessions or 0,
                    "overall_score": 0,
                }, on_conflict="username").execute()
            except Exception:
                pass

            return True
        except Exception as e:
            logger.exception(f"Supabase sync_user_on_auth failed for {user.username}: {e}")
            return False

    @classmethod
    def sync_all_existing_users(cls):
        """
        Syncs all existing local Django users into Supabase Auth.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        synced_count = 0
        for u in User.objects.all():
            if cls.sync_user_on_auth(u, action_type="INITIAL_SYNC"):
                synced_count += 1
        return synced_count
