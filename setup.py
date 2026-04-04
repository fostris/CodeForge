from setuptools import setup, find_packages

setup(
    name="ai-pipeline",
    version="0.1.0",
    description="Hybrid local/cloud LLM-driven pipeline for feature development",
    author="AI Pipeline Contributors",
    author_email="dev@ai-pipeline.local",
    license="MIT",
    
    packages=find_packages(),
    
    python_requires=">=3.12",
    
    install_requires=[
        "langgraph>=0.0.6",
        "langchain-core>=0.1.0",
        "pydantic>=2.0",
        "pydantic-settings>=2.0",
        "httpx>=0.24",
        "aiohttp>=3.9",
        "pyyaml>=6.0",
        "python-dotenv>=1.0",
        "docker>=6.0",
        "pytest>=7.4",
        "pytest-asyncio>=0.21",
        "pytest-cov>=4.1",
        "black>=23.0",
        "isort>=5.12",
        "mypy>=1.4",
        "python-json-logger>=2.0",
    ],
    
    extras_require={
        "cloud": ["litellm>=1.26"],
        "dev": [
            "ipython>=8.18",
            "black[jupyter]",
            "pytest-xdist",
            "coverage",
        ],
    },
    
    entry_points={
        "console_scripts": [
            "ai-pipeline=src.cli:main",
        ],
    },
    
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
    ],
)
