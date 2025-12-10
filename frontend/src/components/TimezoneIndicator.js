import React from 'react';
import { Clock } from 'lucide-react';
import { formatInEST, getCurrentEST } from '../utils/timezone';

const TimezoneIndicator = () => {
  const currentEST = getCurrentEST();
  
  return (
    <div className="flex items-center space-x-2 text-xs text-gray-400">
      <Clock className="w-3 h-3" />
      <span>
        Times shown in EST: {formatInEST(currentEST, 'HH:mm:ss zzz')}
      </span>
    </div>
  );
};

export default TimezoneIndicator;