'use client'

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Building2,
  Pencil,
  Plus,
  RefreshCw,
  ScrollText,
  ShieldCheck,
  Trash2,
} from 'lucide-react'
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
import { PageAlert } from '@/components/dashboard/PageAlert'
import { StatCard } from '@/components/dashboard/StatCard'
import {
  apiClient,
  type GovernanceAuditLogEntry,
  type GovernanceBranch,
  type GovernancePermission,
  type GovernanceRole,
  type GovernanceRolePermissionRow,
} from '@/lib/api/client'
import { formatRelativeTime } from '@/lib/utils'

type PermissionMap = Record<string, string[]>

function normalizePermissionCodes(codes: string[]): string[] {
  return Array.from(new Set(codes.filter(Boolean))).sort((left, right) => left.localeCompare(right))
}

function permissionCodesEqual(left?: string[], right?: string[]): boolean {
  const leftCodes = normalizePermissionCodes(left ?? [])
  const rightCodes = normalizePermissionCodes(right ?? [])

  if (leftCodes.length !== rightCodes.length) {
    return false
  }

  return leftCodes.every((code, index) => code === rightCodes[index])
}

function buildPermissionMap(rows: GovernanceRolePermissionRow[], roleIds: string[]): PermissionMap {
  const map: PermissionMap = {}

  roleIds.forEach((roleId) => {
    map[roleId] = []
  })

  rows.forEach((row) => {
    map[row.role_id] = normalizePermissionCodes(row.permission_codes)
  })

  return map
}

function isImmutableRole(role: GovernanceRole): boolean {
  return role.is_system || ['owner', 'admin', 'member'].includes(role.code)
}

function toFriendlyGovernanceError(error: unknown): string {
  if (error && typeof error === 'object') {
    const message = String((error as { message?: unknown }).message ?? '').trim()
    const status = Number((error as { status?: unknown }).status ?? 0)

    if (status === 400 && /already exists|duplicate/i.test(message)) {
      return 'Data sudah ada. Gunakan kode yang berbeda.'
    }

    if (status === 400 && /still assigned to users/i.test(message)) {
      return 'Role masih dipakai user aktif. Pindahkan user dulu sebelum menghapus role.'
    }

    if (status === 400 && /default roles cannot be deleted/i.test(message)) {
      return 'Role sistem default tidak dapat dihapus.'
    }

    if (status === 400 && /deactivated before permanent deletion/i.test(message)) {
      return 'Branch harus dinonaktifkan terlebih dahulu sebelum dihapus permanen.'
    }

    if (status === 403) {
      return 'Anda tidak memiliki akses governance pada workspace ini.'
    }

    if (status === 404) {
      return 'Data tidak ditemukan atau sudah berubah.'
    }

    if (message) {
      return message
    }
  }

  return 'Terjadi kesalahan saat memproses data governance.'
}

export function GovernancePanel() {
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const [roles, setRoles] = useState<GovernanceRole[]>([])
  const [branches, setBranches] = useState<GovernanceBranch[]>([])
  const [permissionRows, setPermissionRows] = useState<GovernanceRolePermissionRow[]>([])
  const [permissionCatalog, setPermissionCatalog] = useState<GovernancePermission[]>([])
  const [auditLogs, setAuditLogs] = useState<GovernanceAuditLogEntry[]>([])

  const [roleCode, setRoleCode] = useState('')
  const [roleName, setRoleName] = useState('')
  const [isSubmittingRole, setIsSubmittingRole] = useState(false)

  const [branchCode, setBranchCode] = useState('')
  const [branchName, setBranchName] = useState('')
  const [branchLocation, setBranchLocation] = useState('')
  const [isSubmittingBranch, setIsSubmittingBranch] = useState(false)

  const [editingRole, setEditingRole] = useState<GovernanceRole | null>(null)
  const [editRoleName, setEditRoleName] = useState('')
  const [editRoleDescription, setEditRoleDescription] = useState('')
  const [isSavingRoleEdit, setIsSavingRoleEdit] = useState(false)

  const [rolePendingDelete, setRolePendingDelete] = useState<GovernanceRole | null>(null)
  const [isDeletingRole, setIsDeletingRole] = useState(false)

  const [editingBranch, setEditingBranch] = useState<GovernanceBranch | null>(null)
  const [editBranchName, setEditBranchName] = useState('')
  const [editBranchLocation, setEditBranchLocation] = useState('')
  const [isSavingBranchEdit, setIsSavingBranchEdit] = useState(false)

  const [branchPendingDeactivate, setBranchPendingDeactivate] = useState<GovernanceBranch | null>(null)
  const [isDeactivatingBranch, setIsDeactivatingBranch] = useState(false)

  const [branchPendingDelete, setBranchPendingDelete] = useState<GovernanceBranch | null>(null)
  const [isDeletingBranch, setIsDeletingBranch] = useState(false)

  const [processingRoleId, setProcessingRoleId] = useState<string | null>(null)
  const [processingBranchId, setProcessingBranchId] = useState<string | null>(null)

  const [permissionBaseline, setPermissionBaseline] = useState<PermissionMap>({})
  const [permissionDraft, setPermissionDraft] = useState<PermissionMap>({})
  const [permissionSearch, setPermissionSearch] = useState('')
  const [isSavingPermissionMatrix, setIsSavingPermissionMatrix] = useState(false)

  const loadGovernanceData = useCallback(async () => {
    try {
      setError(null)
      const [rolesResponse, matrixResponse, branchesResponse, auditResponse] = await Promise.all([
        apiClient.governance.roles.list(true),
        apiClient.governance.permissions.matrix(true),
        apiClient.governance.branches.list(true),
        apiClient.governance.auditLogs.list({ page: 1, page_size: 10 }),
      ])

      setRoles(rolesResponse.roles)
      setPermissionRows(matrixResponse.roles)
      setPermissionCatalog(matrixResponse.permissions)
      setBranches(branchesResponse.branches)
      setAuditLogs(auditResponse.logs)

      const roleIds = rolesResponse.roles.map((role) => role.id)
      const normalizedMatrix = buildPermissionMap(matrixResponse.roles, roleIds)
      setPermissionBaseline(normalizedMatrix)
      setPermissionDraft(normalizedMatrix)
    } catch (err) {
      setError(toFriendlyGovernanceError(err))
    }
  }, [])

  useEffect(() => {
    const run = async () => {
      setIsLoading(true)
      await loadGovernanceData()
      setIsLoading(false)
    }

    run()
  }, [loadGovernanceData])

  const roleById = useMemo(() => {
    const map = new Map<string, GovernanceRole>()
    roles.forEach((role) => {
      map.set(role.id, role)
    })
    return map
  }, [roles])

  const allPermissionCodes = useMemo(
    () => normalizePermissionCodes(permissionCatalog.map((permission) => permission.code)),
    [permissionCatalog]
  )

  const filteredPermissions = useMemo(() => {
    const keyword = permissionSearch.trim().toLowerCase()
    if (!keyword) {
      return permissionCatalog
    }

    return permissionCatalog.filter((permission) => {
      return (
        permission.code.toLowerCase().includes(keyword)
        || permission.name.toLowerCase().includes(keyword)
        || permission.resource.toLowerCase().includes(keyword)
        || permission.action.toLowerCase().includes(keyword)
      )
    })
  }, [permissionCatalog, permissionSearch])

  const dirtyRoleIds = useMemo(() => {
    const allRoleIds = new Set([...Object.keys(permissionBaseline), ...Object.keys(permissionDraft)])
    return Array.from(allRoleIds).filter((roleId) => {
      return !permissionCodesEqual(permissionBaseline[roleId], permissionDraft[roleId])
    })
  }, [permissionBaseline, permissionDraft])

  const dirtyRoleIdSet = useMemo(() => new Set(dirtyRoleIds), [dirtyRoleIds])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await loadGovernanceData()
    setIsRefreshing(false)
  }

  const handleCreateRole = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const normalizedCode = roleCode.trim().toLowerCase().replace(/\s+/g, '_')
    const normalizedName = roleName.trim()

    if (!normalizedCode || !normalizedName) {
      setError('Role code dan role name wajib diisi.')
      return
    }

    try {
      setIsSubmittingRole(true)
      setError(null)
      setSuccessMessage(null)

      await apiClient.governance.roles.create({
        code: normalizedCode,
        name: normalizedName,
      })

      setRoleCode('')
      setRoleName('')
      setSuccessMessage('Custom role berhasil dibuat.')
      await loadGovernanceData()
    } catch (err) {
      setError(toFriendlyGovernanceError(err))
    } finally {
      setIsSubmittingRole(false)
    }
  }

  const handleCreateBranch = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const normalizedCode = branchCode.trim().toLowerCase().replace(/\s+/g, '_')
    const normalizedName = branchName.trim()

    if (!normalizedCode || !normalizedName) {
      setError('Branch code dan branch name wajib diisi.')
      return
    }

    try {
      setIsSubmittingBranch(true)
      setError(null)
      setSuccessMessage(null)

      await apiClient.governance.branches.create({
        code: normalizedCode,
        name: normalizedName,
        location: branchLocation.trim() || undefined,
      })

      setBranchCode('')
      setBranchName('')
      setBranchLocation('')
      setSuccessMessage('Branch berhasil dibuat.')
      await loadGovernanceData()
    } catch (err) {
      setError(toFriendlyGovernanceError(err))
    } finally {
      setIsSubmittingBranch(false)
    }
  }

  const openRoleEditDialog = (role: GovernanceRole) => {
    setEditingRole(role)
    setEditRoleName(role.name)
    setEditRoleDescription(role.description ?? '')
    setError(null)
    setSuccessMessage(null)
  }

  const handleSaveRoleEdit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!editingRole) {
      return
    }

    const normalizedName = editRoleName.trim()
    const normalizedDescription = editRoleDescription.trim()

    if (normalizedName.length < 2) {
      setError('Nama role minimal 2 karakter.')
      return
    }

    try {
      setIsSavingRoleEdit(true)
      setProcessingRoleId(editingRole.id)
      setError(null)
      setSuccessMessage(null)

      await apiClient.governance.roles.update(editingRole.id, {
        name: normalizedName,
        description: normalizedDescription || undefined,
      })

      setEditingRole(null)
      setSuccessMessage('Role berhasil diperbarui.')
      await loadGovernanceData()
    } catch (err) {
      setError(toFriendlyGovernanceError(err))
    } finally {
      setIsSavingRoleEdit(false)
      setProcessingRoleId(null)
    }
  }

  const handleDeleteRole = async () => {
    if (!rolePendingDelete) {
      return
    }

    try {
      setIsDeletingRole(true)
      setProcessingRoleId(rolePendingDelete.id)
      setError(null)
      setSuccessMessage(null)

      await apiClient.governance.roles.delete(rolePendingDelete.id)

      setRolePendingDelete(null)
      setSuccessMessage('Role berhasil dihapus permanen.')
      await loadGovernanceData()
    } catch (err) {
      setError(toFriendlyGovernanceError(err))
    } finally {
      setIsDeletingRole(false)
      setProcessingRoleId(null)
    }
  }

  const openBranchEditDialog = (branch: GovernanceBranch) => {
    setEditingBranch(branch)
    setEditBranchName(branch.name)
    setEditBranchLocation(branch.location ?? '')
    setError(null)
    setSuccessMessage(null)
  }

  const handleSaveBranchEdit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!editingBranch) {
      return
    }

    const normalizedName = editBranchName.trim()
    const normalizedLocation = editBranchLocation.trim()

    if (normalizedName.length < 2) {
      setError('Nama branch minimal 2 karakter.')
      return
    }

    try {
      setIsSavingBranchEdit(true)
      setProcessingBranchId(editingBranch.id)
      setError(null)
      setSuccessMessage(null)

      await apiClient.governance.branches.update(editingBranch.id, {
        name: normalizedName,
        location: normalizedLocation || undefined,
      })

      setEditingBranch(null)
      setSuccessMessage('Branch berhasil diperbarui.')
      await loadGovernanceData()
    } catch (err) {
      setError(toFriendlyGovernanceError(err))
    } finally {
      setIsSavingBranchEdit(false)
      setProcessingBranchId(null)
    }
  }

  const handleDeactivateBranch = async () => {
    if (!branchPendingDeactivate) {
      return
    }

    try {
      setIsDeactivatingBranch(true)
      setProcessingBranchId(branchPendingDeactivate.id)
      setError(null)
      setSuccessMessage(null)

      await apiClient.governance.branches.update(branchPendingDeactivate.id, {
        is_active: false,
      })

      setBranchPendingDeactivate(null)
      setSuccessMessage('Branch berhasil dinonaktifkan.')
      await loadGovernanceData()
    } catch (err) {
      setError(toFriendlyGovernanceError(err))
    } finally {
      setIsDeactivatingBranch(false)
      setProcessingBranchId(null)
    }
  }

  const handleDeleteBranchPermanently = async () => {
    if (!branchPendingDelete) {
      return
    }

    try {
      setIsDeletingBranch(true)
      setProcessingBranchId(branchPendingDelete.id)
      setError(null)
      setSuccessMessage(null)

      await apiClient.governance.branches.delete(branchPendingDelete.id)

      setBranchPendingDelete(null)
      setSuccessMessage('Branch berhasil dihapus permanen.')
      await loadGovernanceData()
    } catch (err) {
      setError(toFriendlyGovernanceError(err))
    } finally {
      setIsDeletingBranch(false)
      setProcessingBranchId(null)
    }
  }

  const toggleRolePermission = (roleId: string, permissionCode: string) => {
    setPermissionDraft((previous) => {
      const next = { ...previous }
      const codeSet = new Set(previous[roleId] ?? [])

      if (codeSet.has(permissionCode)) {
        codeSet.delete(permissionCode)
      } else {
        codeSet.add(permissionCode)
      }

      next[roleId] = normalizePermissionCodes(Array.from(codeSet))
      return next
    })
  }

  const applyRolePermissionSet = (roleId: string, permissionCodes: string[]) => {
    setPermissionDraft((previous) => ({
      ...previous,
      [roleId]: normalizePermissionCodes(permissionCodes),
    }))
  }

  const handleSaveAllPermissionChanges = async () => {
    if (dirtyRoleIds.length === 0) {
      return
    }

    try {
      setIsSavingPermissionMatrix(true)
      setError(null)
      setSuccessMessage(null)

      const updatePayloads = dirtyRoleIds.map((roleId) => ({
        roleId,
        permissionCodes: permissionDraft[roleId] ?? [],
      }))

      const results = await Promise.allSettled(
        updatePayloads.map((payload) =>
          apiClient.governance.permissions.replaceRolePermissions(payload.roleId, payload.permissionCodes)
        )
      )

      const failedRoleCodes = results.flatMap((result, index) => {
        if (result.status === 'fulfilled') {
          return []
        }

        const roleId = updatePayloads[index].roleId
        const roleCode = roleById.get(roleId)?.code ?? roleId
        return [roleCode]
      })

      if (failedRoleCodes.length > 0) {
        setError(`Gagal menyimpan permission untuk role: ${failedRoleCodes.join(', ')}`)
      } else {
        setSuccessMessage('Permission matrix berhasil disimpan.')
      }

      await loadGovernanceData()
    } catch (err) {
      setError(toFriendlyGovernanceError(err))
    } finally {
      setIsSavingPermissionMatrix(false)
    }
  }

  const handleResetPermissionDraft = () => {
    setPermissionDraft(permissionBaseline)
    setSuccessMessage('Draft permission matrix dikembalikan ke data terakhir tersimpan.')
  }

  const activeRoles = useMemo(() => roles.filter((role) => role.is_active).length, [roles])
  const activeBranches = useMemo(() => branches.filter((branch) => branch.is_active).length, [branches])
  const totalPermissionBindings = useMemo(
    () => permissionRows.reduce((accumulator, row) => accumulator + row.permission_codes.length, 0),
    [permissionRows]
  )

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-10 text-sm text-muted-foreground">Memuat modul governance...</CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {error ? <PageAlert message={error} variant="error" /> : null}
      {successMessage ? <PageAlert message={successMessage} variant="success" /> : null}

      <div className="flex items-center justify-end">
        <Button variant="outline" className="gap-2" onClick={handleRefresh} disabled={isRefreshing}>
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh Governance
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard title="Active Roles" value={activeRoles} subtitle={`${roles.length} total`} tone="accent" />
        <StatCard title="Active Branches" value={activeBranches} subtitle={`${branches.length} total`} tone="success" />
        <StatCard title="Permission Bindings" value={totalPermissionBindings} subtitle="role-permission links" />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
            <CardTitle className="text-lg">Custom Roles</CardTitle>
            <Badge variant="outline" className="gap-1">
              <ShieldCheck className="h-3.5 w-3.5" />
              {roles.length} roles
            </Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <form className="grid grid-cols-1 gap-2 sm:grid-cols-3" onSubmit={handleCreateRole}>
              <Input
                value={roleCode}
                onChange={(event) => setRoleCode(event.target.value)}
                placeholder="role code"
                aria-label="Role code"
              />
              <Input
                value={roleName}
                onChange={(event) => setRoleName(event.target.value)}
                placeholder="role name"
                aria-label="Role name"
              />
              <Button type="submit" className="gap-2" disabled={isSubmittingRole}>
                <Plus className="h-4 w-4" />
                {isSubmittingRole ? 'Menyimpan...' : 'Add Role'}
              </Button>
            </form>

            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Code</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {roles.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-sm text-muted-foreground">
                        Belum ada role pada tenant ini.
                      </TableCell>
                    </TableRow>
                  ) : (
                    roles.map((role) => {
                      const immutableRole = isImmutableRole(role)
                      const roleProcessing = processingRoleId === role.id

                      return (
                        <TableRow key={role.id}>
                          <TableCell className="font-mono text-xs">{role.code}</TableCell>
                          <TableCell>{role.name}</TableCell>
                          <TableCell className="max-w-[220px] text-sm text-muted-foreground">
                            {role.description || '-'}
                          </TableCell>
                          <TableCell>
                            <Badge variant={role.is_active ? 'default' : 'secondary'}>
                              {role.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex flex-wrap justify-end gap-2">
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                aria-label={`Edit role ${role.code}`}
                                disabled={immutableRole || roleProcessing}
                                onClick={() => openRoleEditDialog(role)}
                                className="gap-1"
                              >
                                <Pencil className="h-3.5 w-3.5" />
                                Edit
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                aria-label={`Delete role ${role.code}`}
                                disabled={immutableRole || roleProcessing}
                                onClick={() => setRolePendingDelete(role)}
                                className="gap-1 border-destructive/30 text-destructive hover:bg-destructive/10"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                                Delete
                              </Button>
                            </div>
                            {immutableRole ? (
                              <p className="mt-1 text-xs text-muted-foreground">System role</p>
                            ) : null}
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

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
            <CardTitle className="text-lg">Branches</CardTitle>
            <Badge variant="outline" className="gap-1">
              <Building2 className="h-3.5 w-3.5" />
              {branches.length} branches
            </Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <form className="grid grid-cols-1 gap-2 sm:grid-cols-4" onSubmit={handleCreateBranch}>
              <Input
                value={branchCode}
                onChange={(event) => setBranchCode(event.target.value)}
                placeholder="branch code"
                aria-label="Branch code"
              />
              <Input
                value={branchName}
                onChange={(event) => setBranchName(event.target.value)}
                placeholder="branch name"
                aria-label="Branch name"
              />
              <Input
                value={branchLocation}
                onChange={(event) => setBranchLocation(event.target.value)}
                placeholder="location"
                aria-label="Branch location"
              />
              <Button type="submit" className="gap-2" disabled={isSubmittingBranch}>
                <Plus className="h-4 w-4" />
                {isSubmittingBranch ? 'Menyimpan...' : 'Add Branch'}
              </Button>
            </form>

            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Code</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {branches.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-sm text-muted-foreground">
                        Belum ada branch pada tenant ini.
                      </TableCell>
                    </TableRow>
                  ) : (
                    branches.map((branch) => {
                      const branchProcessing = processingBranchId === branch.id
                      const canDeletePermanently = !branch.is_active

                      return (
                        <TableRow key={branch.id}>
                          <TableCell className="font-mono text-xs">{branch.code}</TableCell>
                          <TableCell>{branch.name}</TableCell>
                          <TableCell>{branch.location || '-'}</TableCell>
                          <TableCell>
                            <Badge variant={branch.is_active ? 'default' : 'secondary'}>
                              {branch.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex flex-wrap justify-end gap-2">
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                aria-label={`Edit branch ${branch.code}`}
                                disabled={branchProcessing}
                                onClick={() => openBranchEditDialog(branch)}
                                className="gap-1"
                              >
                                <Pencil className="h-3.5 w-3.5" />
                                Edit
                              </Button>

                              {branch.is_active ? (
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="outline"
                                  aria-label={`Deactivate branch ${branch.code}`}
                                  disabled={branchProcessing}
                                  onClick={() => setBranchPendingDeactivate(branch)}
                                  className="gap-1"
                                >
                                  Deactivate
                                </Button>
                              ) : null}

                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                aria-label={`Delete branch ${branch.code}`}
                                disabled={!canDeletePermanently || branchProcessing}
                                onClick={() => setBranchPendingDelete(branch)}
                                className="gap-1 border-destructive/30 text-destructive hover:bg-destructive/10"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                                Delete
                              </Button>
                            </div>
                            {!canDeletePermanently ? (
                              <p className="mt-1 text-xs text-muted-foreground">Deactivate first</p>
                            ) : null}
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

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-lg">Permission Matrix Editor</CardTitle>
          <Badge variant="outline">{roles.length} roles</Badge>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="w-full xl:max-w-lg">
              <Input
                value={permissionSearch}
                onChange={(event) => setPermissionSearch(event.target.value)}
                placeholder="Cari permission code, nama, resource, atau action"
                aria-label="Permission search"
              />
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={handleResetPermissionDraft}
                disabled={dirtyRoleIds.length === 0 || isSavingPermissionMatrix}
              >
                Reset Draft
              </Button>
              <Button
                type="button"
                onClick={handleSaveAllPermissionChanges}
                disabled={dirtyRoleIds.length === 0 || isSavingPermissionMatrix}
              >
                {isSavingPermissionMatrix ? 'Saving...' : 'Save All Changes'}
              </Button>
            </div>
          </div>

          <p className="text-xs text-muted-foreground">
            {dirtyRoleIds.length > 0
              ? `${dirtyRoleIds.length} role memiliki perubahan permission.`
              : 'Tidak ada perubahan permission yang belum disimpan.'}
          </p>

          {roles.length === 0 || permissionCatalog.length === 0 ? (
            <p className="text-sm text-muted-foreground">Belum ada data role atau permission untuk ditampilkan.</p>
          ) : filteredPermissions.length === 0 ? (
            <p className="text-sm text-muted-foreground">Tidak ada permission yang cocok dengan filter pencarian.</p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="min-w-[180px]">Role</TableHead>
                    <TableHead className="min-w-[180px]">Quick Actions</TableHead>
                    {filteredPermissions.map((permission) => (
                      <TableHead key={permission.code} className="min-w-[150px]">
                        <div className="space-y-1">
                          <p className="font-mono text-[11px]">{permission.code}</p>
                          <p className="text-[10px] text-muted-foreground">{permission.resource}.{permission.action}</p>
                        </div>
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {roles.map((role) => {
                    const selectedCodes = new Set(permissionDraft[role.id] ?? [])
                    const rowDirty = dirtyRoleIdSet.has(role.id)

                    return (
                      <TableRow key={role.id} className={rowDirty ? 'bg-accent/5' : ''}>
                        <TableCell>
                          <div className="space-y-1">
                            <p className="font-medium text-foreground">{role.name}</p>
                            <p className="font-mono text-xs text-muted-foreground">{role.code}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap items-center gap-2">
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => applyRolePermissionSet(role.id, allPermissionCodes)}
                              disabled={isSavingPermissionMatrix}
                            >
                              All
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              onClick={() => applyRolePermissionSet(role.id, [])}
                              disabled={isSavingPermissionMatrix}
                            >
                              None
                            </Button>
                            {rowDirty ? <Badge variant="secondary">Dirty</Badge> : null}
                          </div>
                        </TableCell>
                        {filteredPermissions.map((permission) => (
                          <TableCell key={`${role.id}-${permission.code}`} className="text-center">
                            <input
                              type="checkbox"
                              checked={selectedCodes.has(permission.code)}
                              onChange={() => toggleRolePermission(role.id, permission.code)}
                              disabled={isSavingPermissionMatrix}
                              aria-label={`Toggle ${permission.code} for role ${role.code}`}
                              className="h-4 w-4 rounded border-border text-accent focus:ring-accent"
                            />
                          </TableCell>
                        ))}
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-lg">Recent Audit Logs</CardTitle>
          <Badge variant="outline" className="gap-1">
            <ScrollText className="h-3.5 w-3.5" />
            {auditLogs.length} latest
          </Badge>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Action</TableHead>
                  <TableHead>Resource</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>When</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditLogs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-sm text-muted-foreground">
                      Belum ada audit logs pada tenant ini.
                    </TableCell>
                  </TableRow>
                ) : (
                  auditLogs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell>
                        <Badge variant="secondary" className="uppercase">
                          {log.action}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{log.resource_type}</TableCell>
                      <TableCell className="font-mono text-xs">{log.actor_user_id || 'system'}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatRelativeTime(log.created_at)}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Dialog
        open={Boolean(editingRole)}
        onOpenChange={(open) => {
          if (!open && !isSavingRoleEdit) {
            setEditingRole(null)
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Role</DialogTitle>
            <DialogDescription>Perbarui nama atau deskripsi role custom.</DialogDescription>
          </DialogHeader>
          <form className="space-y-4" onSubmit={handleSaveRoleEdit}>
            <div className="space-y-2">
              <Label htmlFor="edit-role-name">Edit role name</Label>
              <Input
                id="edit-role-name"
                value={editRoleName}
                onChange={(event) => setEditRoleName(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-role-description">Edit role description</Label>
              <Input
                id="edit-role-description"
                value={editRoleDescription}
                onChange={(event) => setEditRoleDescription(event.target.value)}
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditingRole(null)}
                disabled={isSavingRoleEdit}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSavingRoleEdit}>
                {isSavingRoleEdit ? 'Saving...' : 'Save Changes'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(rolePendingDelete)}
        onOpenChange={(open) => {
          if (!open && !isDeletingRole) {
            setRolePendingDelete(null)
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Role</DialogTitle>
            <DialogDescription>
              Role {rolePendingDelete?.name || '-'} akan dihapus permanen. Tindakan ini tidak dapat dibatalkan.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setRolePendingDelete(null)}
              disabled={isDeletingRole}
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleDeleteRole}
              disabled={isDeletingRole}
              className="border-destructive/30 bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeletingRole ? 'Deleting...' : 'Delete Role'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(editingBranch)}
        onOpenChange={(open) => {
          if (!open && !isSavingBranchEdit) {
            setEditingBranch(null)
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Branch</DialogTitle>
            <DialogDescription>Perbarui nama atau lokasi branch.</DialogDescription>
          </DialogHeader>
          <form className="space-y-4" onSubmit={handleSaveBranchEdit}>
            <div className="space-y-2">
              <Label htmlFor="edit-branch-name">Edit branch name</Label>
              <Input
                id="edit-branch-name"
                value={editBranchName}
                onChange={(event) => setEditBranchName(event.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-branch-location">Edit branch location</Label>
              <Input
                id="edit-branch-location"
                value={editBranchLocation}
                onChange={(event) => setEditBranchLocation(event.target.value)}
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditingBranch(null)}
                disabled={isSavingBranchEdit}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSavingBranchEdit}>
                {isSavingBranchEdit ? 'Saving...' : 'Save Changes'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(branchPendingDeactivate)}
        onOpenChange={(open) => {
          if (!open && !isDeactivatingBranch) {
            setBranchPendingDeactivate(null)
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Deactivate Branch</DialogTitle>
            <DialogDescription>
              Branch {branchPendingDeactivate?.name || '-'} akan dinonaktifkan. Anda dapat mengaktifkannya kembali lewat update branch.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setBranchPendingDeactivate(null)}
              disabled={isDeactivatingBranch}
            >
              Cancel
            </Button>
            <Button type="button" onClick={handleDeactivateBranch} disabled={isDeactivatingBranch}>
              {isDeactivatingBranch ? 'Processing...' : 'Deactivate Branch'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(branchPendingDelete)}
        onOpenChange={(open) => {
          if (!open && !isDeletingBranch) {
            setBranchPendingDelete(null)
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Branch Permanently</DialogTitle>
            <DialogDescription>
              Branch {branchPendingDelete?.name || '-'} akan dihapus permanen. Pastikan branch sudah inactive sebelum melanjutkan.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setBranchPendingDelete(null)}
              disabled={isDeletingBranch}
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleDeleteBranchPermanently}
              disabled={isDeletingBranch}
              className="border-destructive/30 bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeletingBranch ? 'Deleting...' : 'Delete Permanently'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
