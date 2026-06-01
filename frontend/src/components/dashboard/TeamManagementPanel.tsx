'use client'

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Copy, RefreshCw, Search, UserCheck, UserMinus, UserPlus, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PageAlert } from '@/components/dashboard/PageAlert'
import { StatCard } from '@/components/dashboard/StatCard'
import { apiClient, type TenantUser, type TenantUserRole } from '@/lib/api/client'
import { formatRelativeTime } from '@/lib/utils'

interface TeamManagementPanelProps {
  currentUserId: string
  currentUserRole: TenantUserRole
}

function toFriendlyError(error: unknown): string {
  if (error && typeof error === 'object') {
    const message = String((error as { message?: unknown }).message ?? '').trim()
    const status = Number((error as { status?: unknown }).status ?? 0)

    if (status === 400 && /already exists|duplicate|email/i.test(message)) {
      return 'Email sudah terdaftar pada tenant ini.'
    }

    if (status === 400 && /limit|seat/i.test(message)) {
      return 'Seat user sudah penuh. Nonaktifkan user lain terlebih dahulu.'
    }

    if (status === 403) {
      return 'Anda tidak memiliki izin untuk menjalankan aksi ini.'
    }

    if (status === 404) {
      return 'User tidak ditemukan atau statusnya sudah berubah.'
    }

    if (message) {
      return message
    }
  }

  return 'Terjadi kesalahan saat memproses data tim.'
}

export function TeamManagementPanel({ currentUserId, currentUserRole }: TeamManagementPanelProps) {
  const [users, setUsers] = useState<TenantUser[]>([])
  const [maxUsers, setMaxUsers] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isUpdatingId, setIsUpdatingId] = useState<string | null>(null)
  const [isInviteOpen, setIsInviteOpen] = useState(false)
  const [isInviting, setIsInviting] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteName, setInviteName] = useState('')
  const [inviteRole, setInviteRole] = useState<TenantUserRole>('member')
  const [inviteError, setInviteError] = useState<string | null>(null)
  const [temporaryPassword, setTemporaryPassword] = useState<string | null>(null)
  const [invitedEmail, setInvitedEmail] = useState<string | null>(null)
  const [copiedPassword, setCopiedPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  const inviteRoleOptions = useMemo<TenantUserRole[]>(() => {
    if (currentUserRole === 'owner') {
      return ['owner', 'admin', 'member']
    }
    return ['admin', 'member']
  }, [currentUserRole])

  useEffect(() => {
    if (!inviteRoleOptions.includes(inviteRole)) {
      setInviteRole('member')
    }
  }, [inviteRole, inviteRoleOptions])

  const resetInviteState = useCallback(() => {
    setInviteEmail('')
    setInviteName('')
    setInviteRole('member')
    setInviteError(null)
    setTemporaryPassword(null)
    setInvitedEmail(null)
    setCopiedPassword(false)
  }, [])

  const handleInviteDialogChange = useCallback(
    (open: boolean) => {
      setIsInviteOpen(open)
      if (!open) {
        resetInviteState()
      }
    },
    [resetInviteState]
  )

  const loadTeamData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const usersData = await apiClient.users.list(true)
      setUsers(usersData.users)
      setMaxUsers(1000)
    } catch (err) {
      setError(toFriendlyError(err))
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTeamData()
  }, [loadTeamData])

  const activeSeats = useMemo(
    () => users.filter((user) => user.is_active).length,
    [users]
  )

  const availableSeats = Math.max(maxUsers - activeSeats, 0)
  const isSeatFull = maxUsers > 0 && availableSeats === 0

  const filteredUsers = useMemo(() => {
    const keyword = search.trim().toLowerCase()
    if (!keyword) {
      return users
    }

    return users.filter((user) => {
      const fullName = (user.full_name || '').toLowerCase()
      return (
        fullName.includes(keyword)
        || user.email.toLowerCase().includes(keyword)
        || user.role.toLowerCase().includes(keyword)
      )
    })
  }, [search, users])

  const handleDeactivate = async (userId: string) => {
    try {
      setIsUpdatingId(userId)
      setError(null)
      await apiClient.users.deactivate(userId)
      await loadTeamData()
    } catch (err) {
      setError(toFriendlyError(err))
    } finally {
      setIsUpdatingId(null)
    }
  }

  const handleReactivate = async (userId: string) => {
    try {
      setIsUpdatingId(userId)
      setError(null)
      await apiClient.users.reactivate(userId)
      await loadTeamData()
    } catch (err) {
      setError(toFriendlyError(err))
    } finally {
      setIsUpdatingId(null)
    }
  }

  const handleInviteSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const normalizedEmail = inviteEmail.trim().toLowerCase()
    const normalizedName = inviteName.trim()

    if (!normalizedEmail) {
      setInviteError('Email wajib diisi.')
      return
    }

    if (!normalizedName) {
      setInviteError('Nama lengkap wajib diisi.')
      return
    }

    try {
      setIsInviting(true)
      setInviteError(null)

      const result = await apiClient.users.invite({
        email: normalizedEmail,
        full_name: normalizedName,
        role: inviteRole,
        include_temporary_password: true,
      })

      setInvitedEmail(result.user.email)
      setTemporaryPassword(result.temporary_password ?? null)
      setCopiedPassword(false)

      await loadTeamData()
    } catch (err) {
      setInviteError(toFriendlyError(err))
    } finally {
      setIsInviting(false)
    }
  }

  const handleCopyPassword = async () => {
    if (!temporaryPassword) {
      return
    }

    try {
      await navigator.clipboard.writeText(temporaryPassword)
      setCopiedPassword(true)
    } catch {
      setInviteError('Gagal menyalin password. Silakan salin secara manual.')
    }
  }

  const hasInviteSuccess = Boolean(invitedEmail)

  return (
    <div className="space-y-6">
      {error ? <PageAlert message={error} variant="error" /> : null}

      <Dialog open={isInviteOpen} onOpenChange={handleInviteDialogChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{hasInviteSuccess ? 'Undangan Berhasil Dibuat' : 'Invite Team Member'}</DialogTitle>
            <DialogDescription>
              {hasInviteSuccess
                ? 'Simpan temporary password sekarang. Password ini tidak akan ditampilkan lagi.'
                : 'Isi data member baru: email, nama lengkap, dan role.'}
            </DialogDescription>
          </DialogHeader>

          {hasInviteSuccess ? (
            <div className="space-y-4">
              <PageAlert
                variant="success"
                message={`Undangan berhasil dibuat untuk ${invitedEmail}.`}
              />

              {temporaryPassword ? (
                <div className="rounded-xl border border-amber-300 bg-amber-50 p-4">
                  <p className="text-sm font-medium text-foreground">Temporary Password</p>
                  <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center">
                    <code className="inline-flex min-h-10 flex-1 items-center rounded-md border border-border bg-background px-3 py-2 text-sm font-semibold text-foreground">
                      {temporaryPassword}
                    </code>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="gap-2"
                      onClick={handleCopyPassword}
                    >
                      <Copy className="h-4 w-4" />
                      {copiedPassword ? 'Copied' : 'Copy'}
                    </Button>
                  </div>
                  <p className="mt-3 text-xs text-amber-700">
                    Password sementara hanya ditampilkan sekali. Setelah modal ditutup, nilai ini akan dihapus.
                  </p>
                </div>
              ) : (
                <PageAlert
                  variant="warning"
                  message="Temporary password tidak tersedia. Buat ulang undangan jika diperlukan."
                />
              )}

              {inviteError ? <PageAlert message={inviteError} variant="error" /> : null}

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={resetInviteState}
                >
                  Invite Another Member
                </Button>
                <Button
                  type="button"
                  aria-label="Close invite modal"
                  onClick={() => handleInviteDialogChange(false)}
                >
                  Close
                </Button>
              </DialogFooter>
            </div>
          ) : (
            <form className="space-y-4" onSubmit={handleInviteSubmit}>
              <div className="space-y-2">
                <Label htmlFor="invite-email">Email</Label>
                <Input
                  id="invite-email"
                  type="email"
                  value={inviteEmail}
                  onChange={(event) => setInviteEmail(event.target.value)}
                  placeholder="member@noblesoft.test"
                  autoComplete="email"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="invite-full-name">Nama Lengkap</Label>
                <Input
                  id="invite-full-name"
                  value={inviteName}
                  onChange={(event) => setInviteName(event.target.value)}
                  placeholder="Nama lengkap member"
                  autoComplete="name"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="invite-role">Role</Label>
                <Select value={inviteRole} onValueChange={(value) => setInviteRole(value as TenantUserRole)}>
                  <SelectTrigger id="invite-role">
                    <SelectValue placeholder="Pilih role" />
                  </SelectTrigger>
                  <SelectContent>
                    {inviteRoleOptions.map((role) => (
                      <SelectItem key={role} value={role}>
                        {role.charAt(0).toUpperCase() + role.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {inviteError ? <PageAlert message={inviteError} variant="error" /> : null}

              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => handleInviteDialogChange(false)}
                >
                  Batal
                </Button>
                <Button type="submit" className="gap-2 bg-brand-orange hover:bg-brand-orange/90 text-white border-none shadow-sm" disabled={isInviting}>
                  <UserPlus className="h-4 w-4" />
                  {isInviting ? 'Mengundang...' : 'Undang Anggota'}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {isSeatFull ? (
        <PageAlert
          message="Kapasitas seat penuh. Reaktivasi user akan gagal sampai ada seat kosong."
          variant="warning"
        />
      ) : null}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Cari nama, email, atau jabatan..."
            className="pl-10"
          />
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" className="gap-2" onClick={() => handleInviteDialogChange(true)}>
            <UserPlus className="h-4 w-4" />
            Undang Member
          </Button>

          <Button variant="outline" className="gap-2" onClick={loadTeamData} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Muat Ulang
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard title="Seat Aktif" value={activeSeats} subtitle={`dari ${maxUsers} seat`} tone="accent" />
        <StatCard title="Seat Tersedia" value={availableSeats} subtitle="siap digunakan" tone={availableSeats > 0 ? 'success' : 'warning'} />
        <StatCard title="Total Anggota" value={users.length} subtitle="aktif + nonaktif" />
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
          <CardTitle className="text-lg text-brand-teal">Anggota Tim & Karyawan</CardTitle>
          <Badge variant="outline">{filteredUsers.length} ditampilkan</Badge>
        </CardHeader>

        <CardContent className="px-0 pb-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-6">Nama</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Jabatan</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Diperbarui</TableHead>
                  <TableHead className="pr-6 text-right">Aksi</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                      Memuat data anggota tim...
                    </TableCell>
                  </TableRow>
                ) : filteredUsers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                      <div className="mx-auto flex max-w-sm flex-col items-center gap-2">
                        <Users className="h-5 w-5" />
                        <p>Tidak ada user yang cocok dengan filter pencarian.</p>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredUsers.map((user) => {
                    const isCurrentUser = user.id === currentUserId
                    const isOwnerTarget = user.role === 'owner'
                    const ownerProtected = isOwnerTarget && currentUserRole !== 'owner'
                    const isUpdating = isUpdatingId === user.id
                    const canDeactivate = user.is_active && !isCurrentUser && !ownerProtected
                    const canReactivate = !user.is_active && !ownerProtected
                    const seatBlocked = !user.is_active && isSeatFull

                    let hint = ''
                    if (isCurrentUser && user.is_active) {
                      hint = 'Current user tidak bisa dinonaktifkan.'
                    } else if (ownerProtected) {
                      hint = 'Akun owner hanya bisa dikelola owner.'
                    } else if (seatBlocked) {
                      hint = 'Seat penuh, reaktivasi ditolak.'
                    }

                    return (
                      <TableRow key={user.id}>
                        <TableCell className="pl-6">
                          <p className="font-medium text-foreground">{user.full_name || '-'}</p>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">{user.email}</TableCell>
                        <TableCell>
                          <Badge variant={user.role === 'owner' ? 'accent' : user.role === 'admin' ? 'secondary' : 'outline'} className="capitalize">
                            {user.role}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={user.is_active ? 'default' : 'destructive'}>
                            {user.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatRelativeTime(user.updated_at)}
                        </TableCell>
                        <TableCell className="pr-6 text-right">
                          <div className="flex flex-col items-end gap-1">
                            {user.is_active ? (
                              <Button
                                size="sm"
                                variant="outline"
                                className="gap-2 border-destructive/30 text-destructive hover:bg-destructive/10"
                                onClick={() => handleDeactivate(user.id)}
                                disabled={isUpdating || !canDeactivate}
                                aria-label={`Deactivate ${user.email}`}
                              >
                                <UserMinus className="h-4 w-4" />
                                {isUpdating ? 'Processing...' : 'Deactivate'}
                              </Button>
                            ) : (
                              <Button
                                size="sm"
                                className="gap-2"
                                onClick={() => handleReactivate(user.id)}
                                disabled={isUpdating || !canReactivate || seatBlocked}
                                aria-label={`Reactivate ${user.email}`}
                              >
                                <UserCheck className="h-4 w-4" />
                                {isUpdating ? 'Processing...' : 'Reactivate'}
                              </Button>
                            )}

                            {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
