import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Layout from '../components/Layout';
import { API } from '../App';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Book, ExternalLink, Loader2 } from 'lucide-react';

function PublicApiDocs() {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDocs();
  }, []);

  const fetchDocs = async () => {
    try {
      const response = await axios.get(`${API}/docs/public-api`);
      setContent(response.data.content);
    } catch (error) {
      console.error('Error fetching documentation:', error);
      setContent('# Error Loading Documentation\n\nFailed to load the documentation. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-96">
          <div className="flex items-center text-blue-400">
            <Loader2 className="w-6 h-6 mr-2 animate-spin" />
            Loading documentation...
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-3xl font-bold text-white flex items-center">
            <Book className="w-8 h-8 mr-3" />
            Public API Documentation
          </h2>
          <a
            href={`${API}/docs/public-api-example`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:opacity-90 text-white rounded-lg transition-opacity"
          >
            <ExternalLink className="w-4 h-4 mr-2" />
            View Live Example
          </a>
        </div>

        <div className="glass rounded-xl border border-white/10 p-8">
          <div className="prose prose-invert max-w-none">
            <ReactMarkdown
              children={content}
              components={{
                code({ node, inline, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  return !inline && match ? (
                    <SyntaxHighlighter
                      style={vscDarkPlus}
                      language={match[1]}
                      PreTag="div"
                      {...props}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  ) : (
                    <code className="bg-gray-800 px-2 py-1 rounded text-sm" {...props}>
                      {children}
                    </code>
                  );
                },
                h1: ({ node, ...props }) => (
                  <h1 className="text-4xl font-bold text-white mb-6 mt-8" {...props} />
                ),
                h2: ({ node, ...props }) => (
                  <h2 className="text-3xl font-bold text-white mb-4 mt-8 border-b border-white/10 pb-2" {...props} />
                ),
                h3: ({ node, ...props }) => (
                  <h3 className="text-2xl font-semibold text-white mb-3 mt-6" {...props} />
                ),
                h4: ({ node, ...props }) => (
                  <h4 className="text-xl font-semibold text-white mb-2 mt-4" {...props} />
                ),
                p: ({ node, ...props }) => (
                  <p className="text-gray-300 mb-4 leading-relaxed" {...props} />
                ),
                ul: ({ node, ...props }) => (
                  <ul className="list-disc list-inside text-gray-300 mb-4 space-y-2" {...props} />
                ),
                ol: ({ node, ...props }) => (
                  <ol className="list-decimal list-inside text-gray-300 mb-4 space-y-2" {...props} />
                ),
                li: ({ node, ...props }) => (
                  <li className="text-gray-300" {...props} />
                ),
                a: ({ node, ...props }) => (
                  <a className="text-blue-400 hover:text-blue-300 underline" {...props} />
                ),
                table: ({ node, ...props }) => (
                  <div className="overflow-x-auto mb-4">
                    <table className="min-w-full border border-white/10" {...props} />
                  </div>
                ),
                thead: ({ node, ...props }) => (
                  <thead className="bg-white/5" {...props} />
                ),
                th: ({ node, ...props }) => (
                  <th className="border border-white/10 px-4 py-2 text-left text-white font-semibold" {...props} />
                ),
                td: ({ node, ...props }) => (
                  <td className="border border-white/10 px-4 py-2 text-gray-300" {...props} />
                ),
                blockquote: ({ node, ...props }) => (
                  <blockquote className="border-l-4 border-blue-500 pl-4 italic text-gray-400 my-4" {...props} />
                ),
                strong: ({ node, ...props }) => (
                  <strong className="text-white font-bold" {...props} />
                ),
              }}
            />
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default PublicApiDocs;
