-- 灵境导游 数据库初始化脚本

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 游客会话表
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    visitor_id VARCHAR(64),
    platform VARCHAR(20) DEFAULT 'web',
    interests VARCHAR(50)[] DEFAULT '{}',
    session_start TIMESTAMPTZ DEFAULT NOW(),
    session_end TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sessions_visitor ON sessions(visitor_id);

-- 交互记录表
CREATE TABLE IF NOT EXISTS interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES sessions(id),
    query_text TEXT NOT NULL,
    query_mode VARCHAR(10) DEFAULT 'text',
    response_text TEXT NOT NULL,
    rag_sources JSONB DEFAULT '[]',
    emotion_label VARCHAR(10) DEFAULT 'neutral',
    satisfaction INTEGER,
    thinking_time_ms INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interactions_session ON interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_interactions_created ON interactions(created_at);

-- 知识文档表
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(20),
    file_size INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'uploaded',
    chunk_count INTEGER DEFAULT 0,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 知识分块表
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- FAQ 表
CREATE TABLE IF NOT EXISTS faqs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    match_text TEXT,
    tags VARCHAR(50)[] DEFAULT '{}',
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 数字人配置表
CREATE TABLE IF NOT EXISTS avatar_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100),
    appearance VARCHAR(50),
    costume VARCHAR(50),
    voice_type VARCHAR(50),
    speech_rate FLOAT DEFAULT 1.0,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 每日统计表
CREATE TABLE IF NOT EXISTS daily_stats (
    date DATE PRIMARY KEY,
    total_sessions INTEGER DEFAULT 0,
    total_interactions INTEGER DEFAULT 0,
    avg_thinking_time_ms FLOAT DEFAULT 0,
    positive_ratio FLOAT DEFAULT 0,
    top_questions JSONB DEFAULT '[]',
    top_attractions JSONB DEFAULT '[]'
);
