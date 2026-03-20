import React, { useState, useEffect } from 'react';
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

function QAReviewDialog({ open, onOpenChange, call, onSubmit, saving }) {
  const [humanVoiceQuality, setHumanVoiceQuality] = useState('');
  const [humanLatency, setHumanLatency] = useState('');
  const [humanConversationQuality, setHumanConversationQuality] = useState('');
  const [humanNotes, setHumanNotes] = useState('');

  useEffect(() => {
    if (call && open) {
      const qa = call.qaAnalysis || {};
      setHumanVoiceQuality(qa.humanVoiceQuality ?? '');
      setHumanLatency(qa.humanLatency ?? '');
      setHumanConversationQuality(qa.humanConversationQuality ?? '');
      setHumanNotes(qa.humanNotes ?? '');
    }
  }, [call, open]);

  const handleSubmit = () => {
    const vq = parseInt(humanVoiceQuality, 10);
    const lat = parseInt(humanLatency, 10);
    const cq = parseInt(humanConversationQuality, 10);

    if ([vq, lat, cq].some((s) => isNaN(s) || s < 1 || s > 10)) {
      return;
    }

    onSubmit({
      humanVoiceQuality: vq,
      humanLatency: lat,
      humanConversationQuality: cq,
      humanNotes: humanNotes || '',
    });
  };

  const isValid = () => {
    const scores = [humanVoiceQuality, humanLatency, humanConversationQuality].map((s) =>
      parseInt(s, 10)
    );
    return scores.every((s) => !isNaN(s) && s >= 1 && s <= 10);
  };

  const contactName =
    `${call?.contactFirstName || ''} ${call?.contactLastName || ''}`.trim() || 'Unknown';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[#1a1a2e] border-white/10 text-white max-w-md">
        <DialogHeader>
          <DialogTitle>Human QA Review</DialogTitle>
          <DialogDescription className="text-gray-400">
            Call #{call?.id} — {contactName}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="text-sm text-gray-400 mb-1 block">Voice Quality (1-10)</label>
            <Input
              type="number"
              min={1}
              max={10}
              value={humanVoiceQuality}
              onChange={(e) => setHumanVoiceQuality(e.target.value)}
              placeholder="1-10"
              className="bg-black/40 border-white/10 text-white"
            />
          </div>

          <div>
            <label className="text-sm text-gray-400 mb-1 block">Latency (1-10)</label>
            <Input
              type="number"
              min={1}
              max={10}
              value={humanLatency}
              onChange={(e) => setHumanLatency(e.target.value)}
              placeholder="1-10"
              className="bg-black/40 border-white/10 text-white"
            />
          </div>

          <div>
            <label className="text-sm text-gray-400 mb-1 block">
              Conversation Quality (1-10)
            </label>
            <Input
              type="number"
              min={1}
              max={10}
              value={humanConversationQuality}
              onChange={(e) => setHumanConversationQuality(e.target.value)}
              placeholder="1-10"
              className="bg-black/40 border-white/10 text-white"
            />
          </div>

          <div>
            <label className="text-sm text-gray-400 mb-1 block">Notes</label>
            <Textarea
              value={humanNotes}
              onChange={(e) => setHumanNotes(e.target.value)}
              placeholder="Optional review notes..."
              rows={3}
              className="bg-black/40 border-white/10 text-white"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} className="border-white/10 text-gray-300">
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!isValid() || saving}>
            {saving ? 'Saving...' : 'Save Review'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default QAReviewDialog;
