-- JotangNote database initialization example for MySQL 8
-- Only creates tables. No accounts, passwords or demo data.
-- Use a database account with DDL permission to apply it.

CREATE DATABASE IF NOT EXISTS jotang_note
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE jotang_note;

CREATE TABLE IF NOT EXISTS users (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS notes (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content LONGTEXT NOT NULL,
    author VARCHAR(100) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_notes_author (author)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
