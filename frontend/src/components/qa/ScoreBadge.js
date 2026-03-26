import React from 'react';

function ScoreBadge({ score }) {
  if (score === null || score === undefined) {
    return (
      <span className="inline-flex items-center justify-center w-8 h-6 rounded text-xs font-medium bg-white/5 text-gray-500">
        —
      </span>
    );
  }

  let colorClasses = '';
  if (score >= 8) {
    colorClasses = 'bg-emerald-500/20 text-emerald-400';
  } else if (score >= 5) {
    colorClasses = 'bg-yellow-500/20 text-yellow-400';
  } else {
    colorClasses = 'bg-red-500/20 text-red-400';
  }

  return (
    <span className={`inline-flex items-center justify-center w-8 h-6 rounded text-xs font-bold ${colorClasses}`}>
      {score}
    </span>
  );
}

export default ScoreBadge;
