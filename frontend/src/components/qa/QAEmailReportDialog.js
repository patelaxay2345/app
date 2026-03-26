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
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

function QAEmailReportDialog({ open, onOpenChange, onSubmit, sending, callCount }) {
  const [cc, setCc] = useState('');
  const [message, setMessage] = useState('');

  const handleSubmit = () => {
    const ccList = cc
      .split(',')
      .map((e) => e.trim())
      .filter((e) => e.length > 0);
    onSubmit({ cc: ccList.length > 0 ? ccList : null, message: message || null });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[#1a1a2e] border-white/10 text-white max-w-md">
        <DialogHeader>
          <DialogTitle>Send QA Report Email</DialogTitle>
          <DialogDescription className="text-gray-400">
            Send report for {callCount} call{callCount !== 1 ? 's' : ''} to taj@jobtalk.ai
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400 mb-1 block">CC (comma separated)</label>
            <Input
              value={cc}
              onChange={(e) => setCc(e.target.value)}
              placeholder="email1@example.com, email2@example.com"
              className="bg-black/40 border-white/10 text-white"
            />
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
          <Button variant="outline" onClick={() => onOpenChange(false)} className="border-white/10 text-gray-300">
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={sending}>
            {sending ? 'Sending...' : 'Send Report'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default QAEmailReportDialog;
