import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { X } from 'lucide-react';

function QAEmailReportDialog({ open, onOpenChange, onSubmit, sending, callCount, recipients }) {
  const [ccEmails, setCcEmails] = useState([]);
  const [message, setMessage] = useState('');

  const addCcEmail = (value) => {
    const trimmed = value.trim();
    if (trimmed && !ccEmails.includes(trimmed)) {
      setCcEmails((prev) => [...prev, trimmed]);
    }
  };

  const removeCcEmail = (idx) => {
    setCcEmails((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = () => {
    onSubmit({ cc: ccEmails.length > 0 ? ccEmails : null, message: message || null });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[#1a1a2e] border-white/10 text-white max-w-md">
        <DialogHeader>
          <DialogTitle>Send QA Report Email</DialogTitle>
          <DialogDescription asChild>
            <div className="text-gray-400 text-sm">
              <span>Send report for {callCount} call{callCount !== 1 ? 's' : ''} to:</span>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {(recipients || '').split(',').map((e) => e.trim()).filter(Boolean).map((email, i) => (
                  <span key={i} className="inline-flex px-2 py-0.5 rounded-full text-xs bg-blue-500/20 text-blue-300 border border-blue-500/30">
                    {email}
                  </span>
                ))}
                {!(recipients || '').trim() && (
                  <span className="text-gray-500 text-xs italic">No recipients configured</span>
                )}
              </div>
            </div>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400 mb-1 block">CC</label>
            <div className="flex flex-wrap items-center gap-2 p-2 min-h-[42px] bg-black/40 border border-white/10 rounded-md">
              {ccEmails.map((email, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/20 text-blue-300 border border-blue-500/30"
                >
                  {email}
                  <button
                    type="button"
                    onClick={() => removeCcEmail(idx)}
                    className="ml-0.5 hover:text-red-400 transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
              <input
                type="email"
                placeholder={ccEmails.length === 0 ? 'email@example.com' : 'Add another...'}
                className="flex-1 min-w-[150px] bg-transparent border-none outline-none text-white text-sm placeholder:text-gray-500"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addCcEmail(e.target.value);
                    e.target.value = '';
                  }
                }}
              />
            </div>
          </div>

          <div>
            <label className="text-sm text-gray-400 mb-1 block">Custom Message</label>
            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Optional message to include in the report..."
              rows={3}
              className="bg-black/40 border-white/10 text-white"
            />
          </div>
        </div>

        <DialogFooter>
          <Button onClick={() => onOpenChange(false)} className="bg-gray-500/20 hover:bg-gray-500/30 text-gray-400 border border-gray-500/30">
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={sending} className="bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 border border-blue-500/30">
            {sending ? 'Sending...' : 'Send Report'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default QAEmailReportDialog;
