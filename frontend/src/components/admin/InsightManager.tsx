'use client';

import { Database } from 'lucide-react';

export default function InsightManager() {
  return (
    <div className="text-center py-12">
      <Database className="mx-auto h-12 w-12 text-gray-400" />
      <h3 className="mt-2 text-sm font-medium text-gray-900">Insight Management</h3>
      <p className="mt-1 text-sm text-gray-500">
        Review AI-generated insights, validate findings, and manage insight quality.
      </p>
      <div className="mt-6">
        <button className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700">
          Coming Soon
        </button>
      </div>
    </div>
  );
}