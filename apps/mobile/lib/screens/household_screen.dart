import 'package:flutter/material.dart';

import '../core/app_store.dart';
import '../core/models.dart';

class HouseholdScreen extends StatefulWidget {
  const HouseholdScreen({super.key});

  @override
  State<HouseholdScreen> createState() => _HouseholdScreenState();
}

class _HouseholdScreenState extends State<HouseholdScreen> {
  final store = AppStore.instance;
  final _nameController = TextEditingController();
  final _inviteCodeController = TextEditingController();
  String _selectedRole = 'MEMBER';
  String? _generatedInviteCode;
  String _status = '';

  @override
  void initState() {
    super.initState();
    store.refreshHousehold();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _inviteCodeController.dispose();
    super.dispose();
  }

  bool get _canManage {
    final me = store.household?.findMember(store.currentUserId);
    if (me == null) {
      return false;
    }
    return me.role == HouseholdRole.owner || me.role == HouseholdRole.admin;
  }

  Future<void> _createInvitation() async {
    final code = await store.createInvitation(role: _selectedRole);
    if (!mounted) {
      return;
    }
    setState(() {
      if (code != null && code.isNotEmpty) {
        _generatedInviteCode = code;
        _status = '邀请码已生成，7 天内有效';
      } else {
        _status = '生成邀请码失败';
      }
    });
  }

  Future<void> _joinHousehold() async {
    final code = _inviteCodeController.text.trim();
    if (code.isEmpty) {
      setState(() => _status = '请输入邀请码');
      return;
    }
    final ok = await store.joinHousehold(code);
    if (!mounted) {
      return;
    }
    setState(() => _status = ok ? '已加入家庭' : '加入失败，请检查邀请码');
  }

  Future<void> _createHousehold() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      setState(() => _status = '请输入家庭名称');
      return;
    }
    final ok = await store.createHousehold(name);
    if (!mounted) {
      return;
    }
    setState(() => _status = ok ? '已创建新家庭' : '创建家庭失败');
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: store,
      builder: (context, _) {
        final household = store.household;
        return Scaffold(
          appBar: AppBar(title: const Text('家庭管理')),
          body: SafeArea(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          household?.name ?? '未加载家庭',
                          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '家庭 ID: ${household?.householdId ?? '-'}',
                          style: const TextStyle(fontSize: 12, color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                const Text('成员', style: TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                if (household == null || household.members.isEmpty)
                  const Card(child: Padding(padding: EdgeInsets.all(16), child: Text('暂无成员')))
                else
                  Card(
                    child: Column(
                      children: household.members.map((member) {
                        final isMe = member.userId == store.currentUserId;
                        return ListTile(
                          leading: const Icon(Icons.person_outline),
                          title: Text('${member.phoneMasked}${isMe ? '（我）' : ''}'),
                          subtitle: Text('角色：${householdRoleLabel(member.role)}'),
                        );
                      }).toList(),
                    ),
                  ),
                const SizedBox(height: 16),
                if (_canManage) ...[
                  const Text('邀请成员', style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          DropdownButtonFormField<String>(
                            value: _selectedRole,
                            decoration: const InputDecoration(labelText: '邀请角色'),
                            items: const [
                              DropdownMenuItem(value: 'MEMBER', child: Text('成员（可编辑）')),
                              DropdownMenuItem(value: 'VIEWER', child: Text('只读（仅查看）')),
                              DropdownMenuItem(value: 'ADMIN', child: Text('管理员（可管理成员）')),
                            ],
                            onChanged: (value) => setState(() => _selectedRole = value ?? 'MEMBER'),
                          ),
                          const SizedBox(height: 12),
                          ElevatedButton(
                            onPressed: store.loading ? null : _createInvitation,
                            child: const Text('生成邀请码'),
                          ),
                          if (_generatedInviteCode != null) ...[
                            const SizedBox(height: 12),
                            SelectableText(
                              '邀请码：$_generatedInviteCode',
                              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                ],
                const Text('加入其他家庭', style: TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        TextField(
                          controller: _inviteCodeController,
                          decoration: const InputDecoration(labelText: '邀请码', border: OutlineInputBorder()),
                        ),
                        const SizedBox(height: 12),
                        ElevatedButton(
                          onPressed: store.loading ? null : _joinHousehold,
                          child: const Text('加入家庭'),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const Text('创建新家庭', style: TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        TextField(
                          controller: _nameController,
                          decoration: const InputDecoration(labelText: '家庭名称', border: OutlineInputBorder()),
                        ),
                        const SizedBox(height: 12),
                        OutlinedButton(
                          onPressed: store.loading ? null : _createHousehold,
                          child: const Text('创建新家庭（将离开当前家庭）'),
                        ),
                      ],
                    ),
                  ),
                ),
                if (_status.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text(
                    _status,
                    style: TextStyle(
                      color: store.lastError.isNotEmpty ? const Color(0xFFC9410A) : const Color(0xFF2E8B57),
                    ),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}
