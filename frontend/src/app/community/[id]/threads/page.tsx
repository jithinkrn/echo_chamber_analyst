"use client";

import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { ExternalLink, ArrowLeft, TrendingUp, TrendingDown, MessageSquare, ThumbsUp } from 'lucide-react';

interface Thread {
  id: string;
  title: string;
  url: string;
  platform: string;
  author: string;
  published_date: string;
  upvotes: number;
  comment_count: number;
  sentiment_score: number;
  echo_score: number;
}

interface Community {
  id: string;
  name: string;
  platform: string;
}

export default function CommunityThreadsPage() {
  const params = useParams();
  const communityId = params.id as string;
  
  const [threads, setThreads] = useState<Thread[]>([]);
  const [community, setCommunity] = useState<Community | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchThreads = async () => {
      try {
        const response = await fetch(
          `http://localhost:8000/api/v1/community/${communityId}/threads/`,
          {
            headers: {
              'Content-Type': 'application/json'
            }
          }
        );

        if (!response.ok) {
          throw new Error('Failed to fetch threads');
        }

        const data = await response.json();
        setThreads(data.threads);
        setCommunity(data.community);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    if (communityId) {
      fetchThreads();
    }
  }, [communityId]);

  const getSentimentColor = (score: number) => {
    if (score > 0.3) return 'text-green-600 bg-green-50';
    if (score < -0.3) return 'text-red-600 bg-red-50';
    return 'text-gray-600 bg-gray-50';
  };

  const getSentimentIcon = (score: number) => {
    if (score > 0.3) return <TrendingUp className="h-4 w-4" />;
    if (score < -0.3) return <TrendingDown className="h-4 w-4" />;
    return null;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading threads...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600">Error: {error}</p>
          <button
            onClick={() => window.close()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Close Window
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => window.close()}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ArrowLeft className="h-5 w-5 text-gray-600" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {community?.name || 'Community'} Threads
                </h1>
                <p className="text-sm text-gray-500 mt-1">
                  {threads.length} threads · {community?.platform}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Threads List */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {threads.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">No threads found for this community</p>
          </div>
        ) : (
          <div className="space-y-4">
            {threads.map((thread) => (
              <div
                key={thread.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    {/* Title */}
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      {thread.title}
                    </h3>

                    {/* Metadata */}
                    <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
                      <span>by {thread.author}</span>
                      <span>·</span>
                      <span>{thread.published_date}</span>
                      <span>·</span>
                      <span className="capitalize">{thread.platform}</span>
                    </div>

                    {/* Stats */}
                    <div className="flex items-center gap-6 mb-3">
                      <div className="flex items-center gap-2 text-gray-700">
                        <ThumbsUp className="h-4 w-4" />
                        <span className="font-medium">{thread.upvotes}</span>
                        <span className="text-xs text-gray-500">upvotes</span>
                      </div>
                      <div className="flex items-center gap-2 text-gray-700">
                        <MessageSquare className="h-4 w-4" />
                        <span className="font-medium">{thread.comment_count}</span>
                        <span className="text-xs text-gray-500">comments</span>
                      </div>
                      <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${getSentimentColor(thread.sentiment_score)}`}>
                        {getSentimentIcon(thread.sentiment_score)}
                        <span className="text-xs font-medium">
                          Sentiment: {thread.sentiment_score > 0 ? '+' : ''}{thread.sentiment_score.toFixed(2)}
                        </span>
                      </div>
                    </div>

                    {/* View Thread Button */}
                    <a
                      href={thread.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                    >
                      <span>View Original Thread</span>
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>

                  {/* Echo Score Badge */}
                  <div className="flex-shrink-0">
                    <div className="px-4 py-2 bg-purple-100 text-purple-800 rounded-lg text-center">
                      <div className="text-xs font-medium text-purple-600">Echo Score</div>
                      <div className="text-2xl font-bold">{thread.echo_score.toFixed(1)}</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
