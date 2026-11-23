"""One module per language. Each exposes a `Language` with:

    extensions        file suffixes it reads
    is_generated(n)   True for generated files to skip (e.g. *.g.dart)
    declarations(rel, source_bytes) -> list of
        {name, kind, file, from, to, supers: [names], members: {name: [from, to]}}
    (lines are 1-based and inclusive; a member's range includes its doc comment)
"""
import os

from . import dart, java, kotlin, objc, swift

LANGUAGES = [dart.LANGUAGE, swift.LANGUAGE, kotlin.LANGUAGE, java.LANGUAGE, objc.LANGUAGE]


def language_for(filename):
    _, extension = os.path.splitext(filename)
    for language in LANGUAGES:
        if extension in language.extensions:
            return language
    return None
