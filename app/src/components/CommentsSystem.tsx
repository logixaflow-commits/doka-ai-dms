import { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, At, Trash2, Edit2, Reply } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { success, error } from './Toast';

export interface Comment {
  id: string;
  userId: string;
  username: string;
  content: string;
  mentions: string[];
  createdAt: Date;
  updatedAt?: Date;
  parentId?: string;
  replies?: Comment[];
}

interface CommentsSystemProps {
  documentId: string;
  documentName: string;
}

export default function CommentsSystem({ documentId, documentName }: CommentsSystemProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [loading, setLoading] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const availableUsers = ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Williams'];

  useEffect(() => {
    loadComments();
  }, [documentId]);

  const loadComments = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/documents/${documentId}/comments`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to load comments');

      const data = await response.json();
      setComments(data);
    } catch (err) {
      // Use mock data for demo
      setComments(generateMockComments());
    }
  };

  const extractMentions = (text: string): string[] => {
    const mentionRegex = /@(\w+)/g;
    const mentions: string[] = [];
    let match;
    while ((match = mentionRegex.exec(text)) !== null) {
      mentions.push(match[1]);
    }
    return mentions;
  };

  const handleSubmitComment = async () => {
    if (!newComment.trim()) return;

    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const mentions = extractMentions(newComment);

      const response = await fetch(`/api/documents/${documentId}/comments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          content: newComment,
          mentions,
          parent_id: replyTo,
        }),
      });

      if (!response.ok) throw new Error('Failed to post comment');

      const newCommentData: Comment = {
        id: Date.now().toString(),
        userId: 'current-user',
        username: localStorage.getItem('username') || 'You',
        content: newComment,
        mentions,
        createdAt: new Date(),
        parentId: replyTo || undefined,
      };

      if (replyTo) {
        setComments((prev) =>
          prev.map((comment) =>
            comment.id === replyTo
              ? { ...comment, replies: [...(comment.replies || []), newCommentData] }
              : comment
          )
        );
        setReplyTo(null);
      } else {
        setComments((prev) => [newCommentData, ...prev]);
      }

      setNewComment('');
      success('Comment posted successfully');
    } catch (err) {
      error('Failed to post comment');
    } finally {
      setLoading(false);
    }
  };

  const handleEditComment = async (commentId: string) => {
    if (!editContent.trim()) return;

    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const mentions = extractMentions(editContent);

      const response = await fetch(`/api/documents/${documentId}/comments/${commentId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          content: editContent,
          mentions,
        }),
      });

      if (!response.ok) throw new Error('Failed to edit comment');

      setComments((prev) =>
        prev.map((comment) =>
          comment.id === commentId
            ? { ...comment, content: editContent, mentions, updatedAt: new Date() }
            : comment
        )
      );

      setEditingId(null);
      setEditContent('');
      success('Comment updated successfully');
    } catch (err) {
      error('Failed to edit comment');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteComment = async (commentId: string) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/documents/${documentId}/comments/${commentId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to delete comment');

      setComments((prev) => prev.filter((comment) => comment.id !== commentId));
      success('Comment deleted successfully');
    } catch (err) {
      error('Failed to delete comment');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000 / 60);
    
    if (diff < 1) return 'Just now';
    if (diff < 60) return `${diff}m ago`;
    if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
    return date.toLocaleDateString();
  };

  const handleMention = (username: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = newComment;
    const before = text.substring(0, start);
    const after = text.substring(end);
    
    setNewComment(`${before}@${username} ${after}`);
    
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + username.length + 2, start + username.length + 2);
    }, 0);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5" />
          Comments & Discussion
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* New Comment */}
        <div className="space-y-3">
          <div className="flex gap-2 items-center text-sm text-slate-500 dark:text-slate-400">
            <At className="w-4 h-4" />
            <span>Mention users with @username</span>
          </div>
          
          {replyTo && (
            <div className="flex items-center justify-between p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <span className="text-sm text-blue-600 dark:text-blue-400">
                Replying to comment
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setReplyTo(null)}
                className="h-6 w-6 p-0"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          )}

          <Textarea
            ref={textareaRef}
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Write a comment... Use @username to mention users"
            className="min-h-[100px]"
          />

          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              {availableUsers.slice(0, 3).map((user) => (
                <Button
                  key={user}
                  variant="ghost"
                  size="sm"
                  onClick={() => handleMention(user.split(' ')[0])}
                  className="text-xs"
                >
                  @{user.split(' ')[0]}
                </Button>
              ))}
            </div>
            <Button
              onClick={handleSubmitComment}
              disabled={loading || !newComment.trim()}
              size="sm"
            >
              <Send className="w-4 h-4 mr-2" />
              {loading ? 'Posting...' : 'Post Comment'}
            </Button>
          </div>
        </div>

        {/* Comments List */}
        <div className="space-y-4">
          {comments.length === 0 ? (
            <Alert>
              <MessageSquare className="h-4 w-4" />
              <AlertDescription>
                No comments yet. Start the discussion!
              </AlertDescription>
            </Alert>
          ) : (
            comments.map((comment) => (
              <div key={comment.id} className="space-y-3">
                <div className="flex gap-3">
                  <Avatar className="w-8 h-8">
                    <AvatarFallback className="text-xs bg-slate-200 dark:bg-slate-700">
                      {comment.username.substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-900 dark:text-slate-100 text-sm">
                          {comment.username}
                        </span>
                        <span className="text-xs text-slate-500 dark:text-slate-400">
                          {formatTime(comment.createdAt)}
                        </span>
                        {comment.updatedAt && (
                          <span className="text-xs text-slate-400">(edited)</span>
                        )}
                      </div>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setReplyTo(comment.id);
                            textareaRef.current?.focus();
                          }}
                          className="h-6 w-6 p-0"
                        >
                          <Reply className="w-3 h-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setEditingId(comment.id);
                            setEditContent(comment.content);
                          }}
                          className="h-6 w-6 p-0"
                        >
                          <Edit2 className="w-3 h-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteComment(comment.id)}
                          className="h-6 w-6 p-0"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>

                    {editingId === comment.id ? (
                      <div className="space-y-2">
                        <Textarea
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          className="min-h-[60px]"
                        />
                        <div className="flex gap-2">
                          <Button
                            onClick={() => handleEditComment(comment.id)}
                            size="sm"
                            disabled={loading}
                          >
                            Save
                          </Button>
                          <Button
                            onClick={() => {
                              setEditingId(null);
                              setEditContent('');
                            }}
                            variant="outline"
                            size="sm"
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                        {comment.content.split(' ').map((word, i) => {
                          if (word.startsWith('@')) {
                            return (
                              <span key={i} className="text-blue-600 dark:text-blue-400 font-medium">
                                {word}{' '}
                              </span>
                            );
                          }
                          return `${word} `;
                        })}
                      </p>
                    )}

                    {comment.mentions && comment.mentions.length > 0 && (
                      <div className="flex gap-1 flex-wrap">
                        {comment.mentions.map((mention) => (
                          <span
                            key={mention}
                            className="text-xs px-2 py-1 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 rounded-full"
                          >
                            @{mention}
                          </span>
                        ))}
                      </div>
                    )}

                    {comment.replies && comment.replies.length > 0 && (
                      <div className="ml-4 mt-3 space-y-3 border-l-2 border-slate-200 dark:border-slate-700 pl-4">
                        {comment.replies.map((reply) => (
                          <div key={reply.id} className="flex gap-3">
                            <Avatar className="w-6 h-6">
                              <AvatarFallback className="text-xs bg-slate-200 dark:bg-slate-700">
                                {reply.username.substring(0, 2).toUpperCase()}
                              </AvatarFallback>
                            </Avatar>
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-slate-900 dark:text-slate-100 text-xs">
                                  {reply.username}
                                </span>
                                <span className="text-xs text-slate-500 dark:text-slate-400">
                                  {formatTime(reply.createdAt)}
                                </span>
                              </div>
                              <p className="text-xs text-slate-700 dark:text-slate-300 mt-1">
                                {reply.content}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function generateMockComments(): Comment[] {
  const now = new Date();
  return [
    {
      id: '1',
      userId: '2',
      username: 'Jane Smith',
      content: 'This document looks great! @John can you review the financial section?',
      mentions: ['John'],
      createdAt: new Date(now.getTime() - 1000 * 60 * 30),
      replies: [
        {
          id: '2',
          userId: '1',
          username: 'John Doe',
          content: 'Sure, I will review it by end of day.',
          mentions: [],
          createdAt: new Date(now.getTime() - 1000 * 60 * 15),
        },
      ],
    },
    {
      id: '3',
      userId: '3',
      username: 'Bob Johnson',
      content: 'I noticed a few formatting issues in the appendix. Should we fix those before sharing?',
      mentions: [],
      createdAt: new Date(now.getTime() - 1000 * 60 * 60 * 2),
    },
  ];
}
