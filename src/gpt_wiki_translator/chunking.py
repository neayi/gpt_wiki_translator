"""Intelligent chunking of wikitext by sections with token estimation."""
from __future__ import annotations
import re
from typing import List, Tuple

# Simple token estimation (1 token ≈ 4 characters for most languages)
def estimate_tokens(text: str) -> int:
    """Rough estimate of token count. Conservative: 1 token per 3.5 chars."""
    return len(text) // 3

def split_by_sections(wikitext: str) -> List[Tuple[str, str]]:
    """Split wikitext into sections based on == headings ==.
    Returns list of (heading, content) tuples."""
    # Pattern to match wiki headings: ==+ Title ==+
    heading_pattern = re.compile(r'^(={2,6})\s*(.+?)\s*\1\s*$', re.MULTILINE)
    
    sections: List[Tuple[str, str]] = []
    last_end = 0
    last_heading = ""
    
    for match in heading_pattern.finditer(wikitext):
        # Content between last heading and this one
        content = wikitext[last_end:match.start()].strip()
        if content or last_heading:
            sections.append((last_heading, content))
        
        # New heading
        level = len(match.group(1))
        title = match.group(2).strip()
        last_heading = match.group(0)  # Full heading with ==
        last_end = match.end()
    
    # Last section
    content = wikitext[last_end:].strip()
    sections.append((last_heading, content))
    
    return sections

def create_chunks(wikitext: str, max_tokens: int = 7000) -> List[str]:
    """Create intelligent chunks from wikitext, splitting on section boundaries.
    
    Args:
        wikitext: The full wikitext to chunk
        max_tokens: Maximum tokens per chunk (default 7000, safe for 8K context models)
    
    Returns:
        List of wikitext chunks, each under max_tokens
    """
    sections = split_by_sections(wikitext)
    
    if not sections:
        return [wikitext]
    
    chunks: List[str] = []
    current_chunk_parts: List[str] = []
    current_tokens = 0
    
    for heading, content in sections:
        section_text = f"{heading}\n{content}" if heading else content
        section_tokens = estimate_tokens(section_text)
        
        # If single section exceeds max, we need to split it further
        if section_tokens > max_tokens:
            # Save current chunk if any
            if current_chunk_parts:
                chunks.append('\n\n'.join(current_chunk_parts))
                current_chunk_parts = []
                current_tokens = 0
            
            # Split large section by paragraphs
            paragraphs = content.split('\n\n')
            para_chunk_parts: List[str] = [heading] if heading else []
            para_tokens = estimate_tokens(heading) if heading else 0
            
            for para in paragraphs:
                para_tokens_est = estimate_tokens(para)
                
                if para_tokens + para_tokens_est > max_tokens:
                    if para_chunk_parts:
                        chunks.append('\n\n'.join(para_chunk_parts))
                    # Very large paragraph - split by sentences or just include as-is
                    if para_tokens_est > max_tokens:
                        # Force include even if over limit
                        chunks.append(f"{heading}\n{para}" if heading else para)
                    else:
                        para_chunk_parts = [para]
                        para_tokens = para_tokens_est
                else:
                    para_chunk_parts.append(para)
                    para_tokens += para_tokens_est
            
            if para_chunk_parts:
                chunks.append('\n\n'.join(para_chunk_parts))
        
        # Normal case: section fits in current or new chunk
        elif current_tokens + section_tokens > max_tokens:
            # Save current chunk and start new one
            if current_chunk_parts:
                chunks.append('\n\n'.join(current_chunk_parts))
            current_chunk_parts = [section_text]
            current_tokens = section_tokens
        else:
            # Add to current chunk
            current_chunk_parts.append(section_text)
            current_tokens += section_tokens
    
    # Don't forget last chunk
    if current_chunk_parts:
        chunks.append('\n\n'.join(current_chunk_parts))
    
    return chunks if chunks else [wikitext]

def get_chunk_stats(chunks: List[str]) -> dict:
    """Get statistics about chunks."""
    return {
        'count': len(chunks),
        'total_chars': sum(len(c) for c in chunks),
        'total_tokens_est': sum(estimate_tokens(c) for c in chunks),
        'avg_tokens': sum(estimate_tokens(c) for c in chunks) // len(chunks) if chunks else 0,
        'max_tokens': max(estimate_tokens(c) for c in chunks) if chunks else 0,
        'min_tokens': min(estimate_tokens(c) for c in chunks) if chunks else 0,
    }
