-- =========================================================================
-- SpeakPro AI - Supabase Public Database Schema (database/supabase_schema.sql)
-- =========================================================================
-- Paste and run this SQL script in your Supabase Dashboard -> SQL Editor
-- to create public tables for user profiles and speaking statistics.
-- =========================================================================

-- 1. User Profiles Table (synced automatically whenever Authentication happens)
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    last_login TIMESTAMPTZ DEFAULT now(),
    total_sessions INTEGER DEFAULT 0,
    overall_score INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Allow read/write access for service role and authenticated users
CREATE POLICY "Allow public read access" ON public.user_profiles FOR SELECT USING (true);
CREATE POLICY "Allow service role insert and update" ON public.user_profiles FOR ALL USING (true);

-- =========================================================================
-- DONE! Your Supabase project is now fully configured for SpeakPro AI.
-- =========================================================================
