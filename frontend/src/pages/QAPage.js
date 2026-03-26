import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import Layout from '../components/Layout';
import { API } from '../App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import ScoreBadge from '../components/qa/ScoreBadge';
import QAReviewDialog from '../components/qa/QAReviewDialog';
import QAEmailReportDialog from '../components/qa/QAEmailReportDialog';
import {
  Search,
  Play,
  Pause,
  ClipboardCheck,
  Mail,
  Loader2,
  Bot,
  ChevronLeft,
  ChevronRight,
  Filter,
  Volume2,
  VolumeX,
} from 'lucide-react';

const PAGE_SIZE = 10;

function formatDuration(seconds) {
  if (!seconds) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function isVoicemail(call) {
  return !!(call.endReason?.toLowerCase().includes('voicemail') || call.vmBeepAt);
}

function StatusBadge({ call }) {
  if (isVoicemail(call)) {
    return <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-yellow-500/15 text-yellow-400">Voicemail</span>;
  }
  const r = (call.endReason || '').toUpperCase();
  if (r === 'ANSWERED') return <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-green-500/15 text-green-400">Completed</span>;
  if (r === 'UNANSWERED') return <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-gray-500/15 text-gray-400">No Answer</span>;
  if (r === 'WRONGNUMBER') return <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-red-500/15 text-red-400">Wrong #</span>;
  return <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-gray-500/15 text-gray-400">{call.endReason || call.status || '—'}</span>;
}

function QAPage() {
  // Partner selection
  const [partners, setPartners] = useState([]);
  const [selectedPartnerId, setSelectedPartnerId] = useState(
    () => localStorage.getItem('qa_selected_partner') || ''
  );

  // Filters
  const [date, setDate] = useState(() => {
    const stored = localStorage.getItem('qa_date');
    return stored || new Date().toISOString().split('T')[0];
  });
  const [minMinutes, setMinMinutes] = useState(() => {
    const stored = localStorage.getItem('qa_min_minutes');
    return stored ? parseInt(stored, 10) : 2;
  });
  const [scoreFilter, setScoreFilter] = useState('');
  const [completedOnly, setCompletedOnly] = useState(false);
  const [showBadOnly, setShowBadOnly] = useState(false);
  const [totalScoreThreshold, setTotalScoreThreshold] = useState(20);
  const [maxAnalyze, setMaxAnalyze] = useState('');

  // Data
  const [calls, setCalls] = useState([]);
  const [page, setPage] = useState(1);

  // UI states
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(null);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [playingCallId, setPlayingCallId] = useState(null);
  const [loadingAudioId, setLoadingAudioId] = useState(null);
  const [presignedUrls, setPresignedUrls] = useState({});
  const eventSourceRef = useRef(null);

  // Dialogs
  const [reviewCall, setReviewCall] = useState(null);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [savingReview, setSavingReview] = useState(false);
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);

  // Fetch partners on mount
  useEffect(() => {
    const fetchPartners = async () => {
      try {
        const res = await axios.get(`${API}/partners`);
        setPartners(res.data);
      } catch (err) {
        toast.error('Failed to load partners');
      }
    };
    fetchPartners();
  }, []);

  // Persist selections
  useEffect(() => {
    if (selectedPartnerId) {
      localStorage.setItem('qa_selected_partner', selectedPartnerId);
    }
  }, [selectedPartnerId]);

  useEffect(() => {
    localStorage.setItem('qa_date', date);
  }, [date]);

  useEffect(() => {
    localStorage.setItem('qa_min_minutes', String(minMinutes));
  }, [minMinutes]);

  // Cleanup EventSource on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, []);

  // Fetch calls
  const fetchCalls = useCallback(async () => {
    if (!selectedPartnerId) {
      toast.error('Please select a client first');
      return;
    }
    stopAudio();
    setLoading(true);
    setCalls([]);
    setPage(1);
    try {
      const res = await axios.get(
        `${API}/partners/${selectedPartnerId}/qa/calls`,
        { params: { date, minMinutes } }
      );
      setCalls(res.data);
      if (res.data.length === 0) {
        toast.info('No calls found for this date and filter');
      } else {
        toast.success(`Loaded ${res.data.length} calls`);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to fetch QA calls');
    } finally {
      setLoading(false);
    }
  }, [selectedPartnerId, date, minMinutes]);

  // Filtered + paginated calls
  const visibleCalls = useMemo(() => {
    return calls
      .filter((c) => {
        if (completedOnly && isVoicemail(c)) return false;
        if (scoreFilter !== '') {
          const sf = parseInt(scoreFilter, 10);
          if (!isNaN(sf)) {
            const qa = c.qaAnalysis || {};
            const scores = [
              qa.aiVoiceQuality,
              qa.aiLatency,
              qa.aiConversationQuality,
              qa.humanVoiceQuality,
              qa.humanLatency,
              qa.humanConversationQuality,
            ].filter((s) => s != null);
            if (scores.length === 0) return false;
            if (!scores.some((s) => s <= sf)) return false;
          }
        }
        if (showBadOnly) {
          const qa = c.qaAnalysis || {};
          const ai = [qa.aiVoiceQuality, qa.aiLatency, qa.aiConversationQuality];
          if (ai.some((s) => s == null)) return false;
          const total = ai.reduce((sum, s) => sum + s, 0);
          if (total >= totalScoreThreshold) return false;
        }
        return true;
      });
  }, [calls, completedOnly, scoreFilter, showBadOnly, totalScoreThreshold]);

  const totalPages = Math.ceil(visibleCalls.length / PAGE_SIZE);
  const paginatedCalls = useMemo(
    () => visibleCalls.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [visibleCalls, page]
  );

  // Run AI Analysis
  const handleAnalyze = async () => {
    const limit = maxAnalyze !== '' && parseInt(maxAnalyze, 10) > 0
      ? parseInt(maxAnalyze, 10)
      : calls.length;
    const pool = calls.slice(0, limit);
    const unanalyzed = pool.filter((c) => {
      const qa = c.qaAnalysis || {};
      return qa.aiVoiceQuality == null;
    });
    if (unanalyzed.length === 0) {
      toast.info('All calls already have AI analysis');
      return;
    }
    setAnalyzing(true);
    setAnalysisProgress({ total: unanalyzed.length, pending: unanalyzed.length, completed: 0, failed: 0, currentCallId: null });
    try {
      const res = await axios.post(
        `${API}/partners/${selectedPartnerId}/qa/analyze`,
        { callIds: unanalyzed.map((c) => c.id) }
      );
      toast.success(res.data.message);
      // Connect to SSE stream for real-time progress
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      eventSourceRef.current = connectToSSE(selectedPartnerId);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to start analysis');
      setAnalyzing(false);
      setAnalysisProgress(null);
    }
  };

  const connectToSSE = useCallback((partnerId) => {
    const token = localStorage.getItem('token');
    const url = `${API}/partners/${partnerId}/qa/analyze/stream?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);

    es.addEventListener('start', (e) => {
      const data = JSON.parse(e.data);
      setAnalysisProgress({
        total: data.total,
        pending: data.pending,
        completed: 0,
        failed: 0,
        currentCallId: null,
      });
    });

    es.addEventListener('processing', (e) => {
      const data = JSON.parse(e.data);
      setAnalysisProgress((prev) => prev ? { ...prev, currentCallId: data.callId } : prev);
    });

    es.addEventListener('progress', (e) => {
      const data = JSON.parse(e.data);
      setAnalysisProgress((prev) => prev ? {
        ...prev,
        completed: data.completed,
        failed: data.failed,
        pending: data.pending,
        currentCallId: null,
      } : prev);
    });

    es.addEventListener('done', (e) => {
      const data = JSON.parse(e.data);
      es.close();
      eventSourceRef.current = null;
      setAnalyzing(false);
      setAnalysisProgress(null);
      toast.success(`Analysis complete: ${data.completed} done, ${data.failed} failed`);
      fetchCalls();
    });

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) {
        es.close();
        eventSourceRef.current = null;
        // Fallback: check status once
        axios.get(`${API}/partners/${partnerId}/qa/analyze/status`)
          .then((res) => {
            const { summary } = res.data;
            const pending = summary.queued + summary.processing;
            if (pending === 0) {
              setAnalyzing(false);
              setAnalysisProgress(null);
              fetchCalls();
            } else {
              setAnalysisProgress((prev) => prev ? { ...prev, pending } : prev);
              setTimeout(() => {
                eventSourceRef.current = connectToSSE(partnerId);
              }, 2000);
            }
          })
          .catch(() => {
            setAnalyzing(false);
            setAnalysisProgress(null);
            toast.info('Lost connection. Refresh to check analysis results.');
          });
      }
    };

    return es;
  }, [fetchCalls]);

  // Recover analysis state on page load / partner change
  useEffect(() => {
    if (!selectedPartnerId) return;
    let cancelled = false;

    const checkRunningAnalysis = async () => {
      try {
        const res = await axios.get(`${API}/partners/${selectedPartnerId}/qa/analyze/status`);
        const { summary } = res.data;
        const pending = summary.queued + summary.processing;
        if (!cancelled && pending > 0) {
          setAnalyzing(true);
          setAnalysisProgress({
            total: pending,
            pending,
            completed: 0,
            failed: 0,
            currentCallId: null,
          });
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
          }
          eventSourceRef.current = connectToSSE(selectedPartnerId);
        }
      } catch {
        // Silently ignore
      }
    };
    checkRunningAnalysis();

    return () => {
      cancelled = true;
      // Tear down SSE and reset analysis UI when partner changes
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setAnalyzing(false);
      setAnalysisProgress(null);
    };
  }, [selectedPartnerId, connectToSSE]);

  // Human review
  const openReview = (call) => {
    setReviewCall(call);
    setReviewOpen(true);
  };

  const handleReviewSubmit = async (reviewData) => {
    if (!reviewCall) return;
    setSavingReview(true);
    try {
      await axios.patch(
        `${API}/partners/${selectedPartnerId}/qa/calls/${reviewCall.id}/review`,
        reviewData
      );
      toast.success('Review saved');
      setReviewOpen(false);
      // Update local state
      setCalls((prev) =>
        prev.map((c) =>
          c.id === reviewCall.id
            ? {
                ...c,
                qaAnalysis: {
                  ...(c.qaAnalysis || {}),
                  ...reviewData,
                },
              }
            : c
        )
      );
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save review');
    } finally {
      setSavingReview(false);
    }
  };

  // Email report
  const handleEmailReport = async ({ cc, message }) => {
    setSendingEmail(true);
    try {
      const callsData = visibleCalls.map((c) => ({
        id: c.id,
        duration: c.duration,
        campaignName: c.campaignName,
        contactFirstName: c.contactFirstName,
        contactLastName: c.contactLastName,
        contactPhone: c.contactPhone,
        qaAnalysis: c.qaAnalysis || null,
      }));

      const partnerName = partners.find((p) => p.id === selectedPartnerId)?.partnerName;

      await axios.post(`${API}/partners/${selectedPartnerId}/qa/email-report`, {
        calls: callsData,
        scoreFilter: scoreFilter ? parseInt(scoreFilter, 10) : null,
        date,
        cc,
        message,
        partnerName,
      });
      toast.success('QA report email sent');
      setEmailDialogOpen(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send email');
    } finally {
      setSendingEmail(false);
    }
  };

  // Audio player state
  const audioRef = useRef(null);
  const [audioProgress, setAudioProgress] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [audioCurrentTime, setAudioCurrentTime] = useState(0);
  const [isAudioPaused, setIsAudioPaused] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [audioVolume, setAudioVolume] = useState(1);
  const progressIntervalRef = useRef(null);

  const formatTime = (secs) => {
    if (!secs || !isFinite(secs)) return '0:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${String(s).padStart(2, '0')}`;
  };

  const startProgressTracking = () => {
    clearInterval(progressIntervalRef.current);
    progressIntervalRef.current = setInterval(() => {
      const audio = audioRef.current;
      if (audio && audio.duration) {
        setAudioCurrentTime(audio.currentTime);
        setAudioProgress((audio.currentTime / audio.duration) * 100);
      }
    }, 250);
  };

  const destroyAudio = () => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.pause();
    // Remove all listeners so the dying element can't fire stale events
    audio.onloadedmetadata = null;
    audio.onended = null;
    audio.onerror = null;
    // Don't set src='' — that triggers MEDIA_ELEMENT_ERROR on the old element.
    // Just remove the reference; the browser will GC it.
    audio.removeAttribute('src');
    audio.load(); // reset internal state without triggering error
    audioRef.current = null;
  };

  const playAudio = (callId, url, contentType) => {
    destroyAudio();
    clearInterval(progressIntervalRef.current);
    setAudioProgress(0);
    setAudioCurrentTime(0);
    setAudioDuration(0);

    const audio = new Audio();
    audio.preload = 'auto';
    audioRef.current = audio;
    audio.volume = audioVolume;
    audio.muted = isMuted;

    audio.onloadedmetadata = () => setAudioDuration(audio.duration);
    audio.onended = () => {
      setPlayingCallId(null);
      setIsAudioPaused(true);
      setAudioProgress(100);
      clearInterval(progressIntervalRef.current);
    };
    audio.onerror = () => {
      // Ignore errors from a destroyed element (no src)
      if (!audio.src && !audio.querySelector('source')) return;
      const err = audio.error;
      console.error('[QA-AUDIO] error:', err?.code, err?.message);
      toast.error('Failed to play recording');
      setPlayingCallId(null);
      setIsAudioPaused(true);
      clearInterval(progressIntervalRef.current);
    };

    if (contentType) {
      const source = document.createElement('source');
      source.src = url;
      source.type = contentType;
      audio.appendChild(source);
    } else {
      audio.src = url;
    }

    audio.load();

    // Wait for enough data before calling play() to avoid interruption race
    const attemptPlay = () => {
      audio.play().then(() => {
        setIsAudioPaused(false);
        startProgressTracking();
      }).catch((err) => {
        // AbortError = play() interrupted by pause/new load — safe to ignore
        if (err.name === 'AbortError') return;
        console.error('[QA-AUDIO] play() failed:', err.message);
        setPlayingCallId(null);
        setIsAudioPaused(true);
      });
    };

    if (audio.readyState >= 2) {
      attemptPlay();
    } else {
      audio.oncanplay = () => {
        audio.oncanplay = null;
        attemptPlay();
      };
    }

    setPlayingCallId(callId);
    setIsAudioPaused(false);
  };

  const stopAudio = () => {
    destroyAudio();
    setPlayingCallId(null);
    setIsAudioPaused(true);
    clearInterval(progressIntervalRef.current);
    setAudioProgress(0);
    setAudioCurrentTime(0);
    setAudioDuration(0);
  };

  const handleSeek = (e) => {
    const audio = audioRef.current;
    if (!audio || !audio.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(1, x / rect.width));
    audio.currentTime = pct * audio.duration;
    setAudioCurrentTime(audio.currentTime);
    setAudioProgress(pct * 100);
  };

  const toggleMute = () => {
    const next = !isMuted;
    setIsMuted(next);
    if (audioRef.current) audioRef.current.muted = next;
  };

  const handleVolumeChange = (e) => {
    const val = parseFloat(e.target.value);
    setAudioVolume(val);
    if (audioRef.current) audioRef.current.volume = val;
    if (val === 0) setIsMuted(true);
    else if (isMuted) setIsMuted(false);
  };

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      clearInterval(progressIntervalRef.current);
      destroyAudio();
    };
  }, []);

  const toggleAudio = async (call) => {
    // Toggle off if already playing
    if (playingCallId === call.id) {
      stopAudio();
      return;
    }

    // Stop any currently playing audio
    stopAudio();

    // If we already have a presigned URL cached, play immediately
    if (presignedUrls[call.id]) {
      playAudio(call.id, presignedUrls[call.id].url, presignedUrls[call.id].contentType);
      return;
    }

    // Check if partner has S3 config enabled
    const partner = partners.find((p) => p.id === selectedPartnerId);
    const hasS3 = partner?.s3Config?.enabled;

    if (!hasS3) {
      // No S3 config — use recording URL directly
      setPresignedUrls((prev) => ({ ...prev, [call.id]: { url: call.recordingUrl, contentType: null } }));
      playAudio(call.id, call.recordingUrl, null);
      return;
    }

    // Get a direct-playable URL (public URL as-is, or presigned for private S3)
    setLoadingAudioId(call.id);
    try {
      const res = await axios.get(
        `${API}/partners/${selectedPartnerId}/qa/presigned-url`,
        { params: { url: call.recordingUrl } }
      );
      const { presignedUrl, contentType } = res.data;
      setPresignedUrls((prev) => ({ ...prev, [call.id]: { url: presignedUrl, contentType } }));
      playAudio(call.id, presignedUrl, contentType);
    } catch (err) {
      console.log("Failed to load recording:", err)
      toast.error(err.response?.data?.detail || 'Failed to load recording');
    } finally {
      setLoadingAudioId(null);
    }
  };

  const selectedPartnerName = partners.find((p) => p.id === selectedPartnerId)?.partnerName;

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              <ClipboardCheck className="w-7 h-7 text-blue-400" />
              QA Dashboard
            </h2>
            <p className="text-gray-400 text-sm mt-1">
              Review call quality and AI analysis scores
            </p>
          </div>
        </div>

        {/* Controls Row */}
        <div className="glass rounded-xl border border-white/10 p-4">
          <div className="flex flex-wrap items-end gap-4">
            {/* Client Dropdown */}
            <div className="flex-1 min-w-[200px]">
              <label className="text-sm text-gray-400 mb-1 block">Client</label>
              <select
                value={selectedPartnerId}
                onChange={(e) => {
                  stopAudio();
                  setSelectedPartnerId(e.target.value);
                  setCalls([]);
                  setPage(1);
                }}
                className="w-full bg-black/40 border border-white/10 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="">Select a client...</option>
                {partners.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.partnerName}
                  </option>
                ))}
              </select>
            </div>

            {/* Date */}
            <div className="min-w-[160px]">
              <label className="text-sm text-gray-400 mb-1 block">Date</label>
              <Input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="bg-black/40 border-white/10 text-white"
              />
            </div>

            {/* Min Minutes */}
            <div className="w-[100px]">
              <label className="text-sm text-gray-400 mb-1 block">Min. Minutes</label>
              <Input
                type="number"
                min={0}
                value={minMinutes}
                onChange={(e) => setMinMinutes(parseInt(e.target.value, 10) || 0)}
                className="bg-black/40 border-white/10 text-white"
              />
            </div>

            {/* Submit */}
            <Button
              onClick={fetchCalls}
              disabled={loading || !selectedPartnerId}
              className="h-9"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              <span className="ml-1">Load Calls</span>
            </Button>
          </div>
        </div>

        {/* Filters + Actions */}
        {calls.length > 0 && (
          <div className="glass rounded-xl border border-white/10 p-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-400">Filters:</span>
              </div>

              {/* Score filter */}
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500">Score ≤</label>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  value={scoreFilter}
                  onChange={(e) => {
                    setScoreFilter(e.target.value);
                    setPage(1);
                  }}
                  placeholder="—"
                  className="w-16 h-8 text-xs bg-black/40 border-white/10 text-white"
                />
              </div>

              {/* Completed only */}
              <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={completedOnly}
                  onChange={(e) => {
                    setCompletedOnly(e.target.checked);
                    setPage(1);
                  }}
                  className="rounded"
                />
                Hide voicemails
              </label>

              {/* Bad calls only */}
              <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showBadOnly}
                  onChange={(e) => {
                    setShowBadOnly(e.target.checked);
                    setPage(1);
                  }}
                  className="rounded"
                />
                Bad calls only
                {showBadOnly && (
                  <span className="text-gray-500">
                    (total &lt;
                    <input
                      type="number"
                      value={totalScoreThreshold}
                      onChange={(e) => setTotalScoreThreshold(parseInt(e.target.value, 10) || 0)}
                      className="w-10 mx-1 text-xs bg-black/40 border border-white/10 text-white rounded px-1"
                    />
                    )
                  </span>
                )}
              </label>

              <div className="flex-1" />

              {/* Stats */}
              <span className="text-xs text-gray-500">
                {visibleCalls.length} of {calls.length} calls
              </span>

              {/* Max to analyze */}
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-500">Max analyze</label>
                <Input
                  type="number"
                  min={1}
                  step={1}
                  value={maxAnalyze}
                  onChange={(e) => setMaxAnalyze(e.target.value === '' ? '' : e.target.value)}
                  placeholder="All"
                  className="w-16 h-8 text-xs bg-black/40 border-white/10 text-white"
                />
              </div>

              {/* Action buttons */}
              <Button
                size="sm"
                variant="outline"
                onClick={handleAnalyze}
                disabled={analyzing}
                className="border-white/10 text-gray-300 text-xs"
              >
                {analyzing ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Bot className="w-3 h-3" />
                )}
                <span className="ml-1">
                  {analyzing && analysisProgress
                    ? `Analyzing... ${analysisProgress.pending} pending`
                    : analyzing
                    ? 'Analyzing...'
                    : 'Run AI Analysis'}
                </span>
              </Button>

              <Button
                size="sm"
                variant="outline"
                onClick={() => setEmailDialogOpen(true)}
                disabled={visibleCalls.length === 0}
                className="border-white/10 text-gray-300 text-xs"
              >
                <Mail className="w-3 h-3" />
                <span className="ml-1">Email Report</span>
              </Button>
            </div>
          </div>
        )}

        {/* Analysis Progress Bar */}
        {analyzing && analysisProgress && (
          <div className="glass rounded-xl border border-white/10 p-4">
            <div className="flex items-center gap-3">
              <Loader2 className="w-4 h-4 animate-spin text-blue-400 flex-shrink-0" />
              <div className="flex-1">
                <div className="flex justify-between text-xs text-gray-400 mb-1">
                  <span>
                    {analysisProgress.currentCallId
                      ? `Processing call #${analysisProgress.currentCallId}`
                      : 'Waiting...'}
                  </span>
                  <span>
                    {analysisProgress.pending} pending
                    {analysisProgress.completed > 0 && ` · ${analysisProgress.completed} done`}
                    {analysisProgress.failed > 0 && ` · ${analysisProgress.failed} failed`}
                  </span>
                </div>
                <div className="w-full bg-white/10 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                    style={{
                      width: `${analysisProgress.total > 0 ? ((analysisProgress.total - analysisProgress.pending) / analysisProgress.total) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!loading && calls.length === 0 && selectedPartnerId && (
          <div className="glass rounded-xl border border-white/10 p-12 text-center">
            <ClipboardCheck className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">
              Click "Load Calls" to fetch QA data for the selected date
            </p>
          </div>
        )}

        {!selectedPartnerId && (
          <div className="glass rounded-xl border border-white/10 p-12 text-center">
            <ClipboardCheck className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">Select a client to begin</p>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="glass rounded-xl border border-white/10 p-12 text-center">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin mx-auto mb-3" />
            <p className="text-gray-400">Loading calls...</p>
          </div>
        )}

        {/* Calls Table */}
        {paginatedCalls.length > 0 && (
          <div className="glass rounded-xl border border-white/10 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 bg-white/5">
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">ID</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Contact</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Campaign</th>
                    <th className="text-center px-3 py-3 text-gray-400 font-medium">Duration</th>
                    <th className="text-center px-3 py-3 text-gray-400 font-medium">Status</th>
                    <th className="text-center px-3 py-3 text-gray-400 font-medium" colSpan={3}>
                      <span className="text-blue-400">AI Scores</span>
                    </th>
                    <th className="text-center px-3 py-3 text-gray-400 font-medium" colSpan={3}>
                      <span className="text-purple-400">Human Scores</span>
                    </th>
                    <th className="text-left px-3 py-3 text-gray-400 font-medium">AI Notes</th>
                    <th className="text-center px-3 py-3 text-gray-400 font-medium">Actions</th>
                  </tr>
                  <tr className="border-b border-white/10 bg-white/[0.02]">
                    <th className="px-4 py-1" />
                    <th className="px-4 py-1" />
                    <th className="px-4 py-1" />
                    <th className="px-3 py-1" />
                    <th className="px-3 py-1" />
                    <th className="px-2 py-1 text-center text-[10px] text-blue-400/70 font-normal">Voice</th>
                    <th className="px-2 py-1 text-center text-[10px] text-blue-400/70 font-normal">Latency</th>
                    <th className="px-2 py-1 text-center text-[10px] text-blue-400/70 font-normal">Conv.</th>
                    <th className="px-2 py-1 text-center text-[10px] text-purple-400/70 font-normal">Voice</th>
                    <th className="px-2 py-1 text-center text-[10px] text-purple-400/70 font-normal">Latency</th>
                    <th className="px-2 py-1 text-center text-[10px] text-purple-400/70 font-normal">Conv.</th>
                    <th className="px-3 py-1" />
                    <th className="px-3 py-1" />
                  </tr>
                </thead>
                <tbody>
                  {paginatedCalls.map((call) => {
                    const qa = call.qaAnalysis || {};
                    const contactName =
                      `${call.contactFirstName || ''} ${call.contactLastName || ''}`.trim() ||
                      '—';
                    const vm = isVoicemail(call);
                    return (
                      <React.Fragment key={call.id}>
                        <tr className="border-b border-white/5 hover:bg-white/[0.03] transition-colors">
                          <td className="px-4 py-3 text-gray-300 font-mono text-xs">
                            {call.id}
                          </td>
                          <td className="px-4 py-3">
                            <div className="text-white text-sm">{contactName}</div>
                            <div className="text-gray-500 text-xs">{call.contactPhone || ''}</div>
                          </td>
                          <td className="px-4 py-3 text-gray-300 text-xs max-w-[200px] truncate">
                            {call.campaignName || '—'}
                          </td>
                          <td className="px-3 py-3 text-center text-gray-300 text-xs">
                            {formatDuration(call.duration)}
                          </td>
                          <td className="px-3 py-3 text-center">
                            <StatusBadge call={call} />
                          </td>
                          {/* AI Scores */}
                          <td className="px-2 py-3 text-center">
                            <ScoreBadge score={qa.aiVoiceQuality} />
                          </td>
                          <td className="px-2 py-3 text-center">
                            <ScoreBadge score={qa.aiLatency} />
                          </td>
                          <td className="px-2 py-3 text-center">
                            <ScoreBadge score={qa.aiConversationQuality} />
                          </td>
                          {/* Human Scores */}
                          <td className="px-2 py-3 text-center">
                            <ScoreBadge score={qa.humanVoiceQuality} />
                          </td>
                          <td className="px-2 py-3 text-center">
                            <ScoreBadge score={qa.humanLatency} />
                          </td>
                          <td className="px-2 py-3 text-center">
                            <ScoreBadge score={qa.humanConversationQuality} />
                          </td>
                          {/* AI Notes */}
                          <td className="px-3 py-3 text-gray-400 text-xs max-w-[200px]">
                            {qa.aiNotes || '—'}
                          </td>
                          {/* Actions */}
                          <td className="px-3 py-3 text-center">
                            <div className="flex items-center justify-between gap-1">
                              <button
                                onClick={() => openReview(call)}
                                title="Human Review"
                                className="p-1.5 rounded-md hover:bg-white/10 text-gray-400 hover:text-blue-400 transition-colors"
                              >
                                <ClipboardCheck className="w-4 h-4" />
                              </button>
                              {call.recordingUrl && (
                                <button
                                  onClick={() => toggleAudio(call)}
                                  disabled={loadingAudioId === call.id}
                                  title="Play Recording"
                                  className="p-1.5 rounded-md hover:bg-white/10 text-gray-400 hover:text-green-400 transition-colors"
                                >
                                  {loadingAudioId === call.id ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : playingCallId === call.id ? (
                                    <Pause className="w-4 h-4" />
                                  ) : (
                                    <Play className="w-4 h-4" />
                                  )}
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                        {/* Audio player track row */}
                        {playingCallId === call.id && (
                          <tr className="border-b border-white/5 bg-white/[0.02]">
                            <td colSpan={13} className="px-4 py-2">
                              <div className="flex items-center gap-3">
                                {/* Play / Pause */}
                                <button
                                  onClick={() => {
                                    const audio = audioRef.current;
                                    if (!audio) return;
                                    if (audio.paused) {
                                      audio.play();
                                      setIsAudioPaused(false);
                                      startProgressTracking();
                                    } else {
                                      audio.pause();
                                      setIsAudioPaused(true);
                                      clearInterval(progressIntervalRef.current);
                                    }
                                  }}
                                  className="flex-shrink-0 w-8 h-8 rounded-full bg-green-500/20 text-green-400 hover:bg-green-500/30 flex items-center justify-center transition-colors"
                                >
                                  {!isAudioPaused ? (
                                    <Pause className="w-4 h-4" />
                                  ) : (
                                    <Play className="w-4 h-4 ml-0.5" />
                                  )}
                                </button>

                                {/* Current time */}
                                <span className="text-xs text-gray-400 font-mono w-10 text-right flex-shrink-0">
                                  {formatTime(audioCurrentTime)}
                                </span>

                                {/* Progress bar */}
                                <div
                                  className="flex-1 h-2 bg-white/10 rounded-full cursor-pointer group relative"
                                  onClick={handleSeek}
                                >
                                  <div
                                    className="h-full bg-green-500 rounded-full relative transition-[width] duration-200"
                                    style={{ width: `${audioProgress}%` }}
                                  >
                                    <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow opacity-0 group-hover:opacity-100 transition-opacity" />
                                  </div>
                                </div>

                                {/* Duration */}
                                <span className="text-xs text-gray-500 font-mono w-10 flex-shrink-0">
                                  {formatTime(audioDuration)}
                                </span>

                                {/* Volume */}
                                <button
                                  onClick={toggleMute}
                                  className="flex-shrink-0 text-gray-400 hover:text-white transition-colors"
                                >
                                  {isMuted || audioVolume === 0 ? (
                                    <VolumeX className="w-4 h-4" />
                                  ) : (
                                    <Volume2 className="w-4 h-4" />
                                  )}
                                </button>
                                <input
                                  type="range"
                                  min="0"
                                  max="1"
                                  step="0.05"
                                  value={isMuted ? 0 : audioVolume}
                                  onChange={handleVolumeChange}
                                  className="w-16 h-1 accent-green-500 flex-shrink-0"
                                />

                                {/* Stop / Close */}
                                <button
                                  onClick={() => stopAudio()}
                                  className="flex-shrink-0 text-gray-500 hover:text-red-400 text-xs transition-colors"
                                  title="Stop"
                                >
                                  ✕
                                </button>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-white/10">
                <span className="text-xs text-gray-500">
                  Page {page} of {totalPages}
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="border-white/10 text-gray-300 h-7 px-2"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="border-white/10 text-gray-300 h-7 px-2"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Dialogs */}
      <QAReviewDialog
        open={reviewOpen}
        onOpenChange={setReviewOpen}
        call={reviewCall}
        onSubmit={handleReviewSubmit}
        saving={savingReview}
      />

      <QAEmailReportDialog
        open={emailDialogOpen}
        onOpenChange={setEmailDialogOpen}
        onSubmit={handleEmailReport}
        sending={sendingEmail}
        callCount={visibleCalls.length}
      />
    </Layout>
  );
}

export default QAPage;
