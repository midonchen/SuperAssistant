import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../core/app_store.dart';
import '../core/models.dart';

enum VoiceState { idle, recording, parsing, success, failure, lowConfidence }

class VoiceModalScreen extends StatefulWidget {
  const VoiceModalScreen({super.key});

  @override
  State<VoiceModalScreen> createState() => _VoiceModalScreenState();
}

class _VoiceModalScreenState extends State<VoiceModalScreen> {
  final store = AppStore.instance;
  final random = Random();

  VoiceState _state = VoiceState.idle;
  List<ParsedEntity> _entities = [];
  String _rawText = '';
  String _sessionId = '';
  bool _confirming = false;
  Timer? _recordingTimeout;

  @override
  void dispose() {
    _recordingTimeout?.cancel();
    super.dispose();
  }

  void _startRecording() {
    setState(() {
      _state = VoiceState.recording;
      _entities = [];
      _rawText = '';
      _sessionId = '';
    });
    _recordingTimeout?.cancel();
    _recordingTimeout = Timer(const Duration(seconds: 6), _stopRecording);
  }

  Future<void> _stopRecording() async {
    if (_state != VoiceState.recording) {
      return;
    }
    setState(() => _state = VoiceState.parsing);

    final args = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;
    final modeArg = args?['mode'] as String?;
    final specificItem = args?['itemKey'] as ItemKey?;

    try {
      await Future<void>.delayed(const Duration(milliseconds: 500));
      if (!mounted) {
        return;
      }

      if (specificItem != null && modeArg == 'calibrate') {
        final value = (1 + random.nextInt(6)).toDouble();
        _sessionId = 'local-cal-${DateTime.now().millisecondsSinceEpoch}';
        _entities = [
          ParsedEntity(
            itemKey: specificItem,
            operation: Operation.set,
            value: value,
            unit: store.findItem(specificItem)?.unit ?? '个',
            confidence: 0.93,
            parseSessionId: _sessionId,
          ),
        ];
        _rawText = '${kItemLabel[specificItem]}还有${value.toStringAsFixed(0)}';
        setState(() => _state = VoiceState.success);
        return;
      }

      final result = await store.parseVoice(
        audioUrl: 'ios://recordings/${DateTime.now().millisecondsSinceEpoch}.m4a',
        locale: 'zh-CN',
      );
      if (!mounted) {
        return;
      }

      _sessionId = result.sessionId;
      _entities = result.entities.map((entity) => entity.withSessionId(_sessionId)).toList();
      if (_entities.isEmpty) {
        setState(() => _state = VoiceState.failure);
        return;
      }

      _rawText = _entities
          .map((entity) => '${kItemLabel[entity.itemKey]} ${entity.normalizedValue.toStringAsFixed(1)} ${entity.normalizedUnit}')
          .join('，');
      final hasLowConfidence = result.confidence < 0.8 || _entities.any((entity) => entity.confidence < 0.8);
      setState(() => _state = hasLowConfidence ? VoiceState.lowConfidence : VoiceState.success);
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() => _state = VoiceState.failure);
    }
  }

  Future<void> _confirm() async {
    if (_confirming) {
      return;
    }
    setState(() => _confirming = true);
    try {
      await store.confirmParsedEntities(
        sessionId: _sessionId,
        entities: _entities,
        source: ActionSource.voice,
        rawText: _rawText,
      );
      if (!mounted) {
        return;
      }
      Navigator.pop(context);
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() => _state = VoiceState.failure);
    } finally {
      if (mounted) {
        setState(() => _confirming = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final canDismiss = _state != VoiceState.recording;
    return WillPopScope(
      onWillPop: () async => canDismiss,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('语音录入'),
          leading: IconButton(
            onPressed: canDismiss ? () => Navigator.pop(context) : null,
            icon: const Icon(Icons.close),
          ),
        ),
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _stateBadge(),
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        const SizedBox(height: 8),
                        _waveView(),
                        const SizedBox(height: 14),
                        Text(_rawText.isEmpty ? '按住录音按钮开始语音录入' : _rawText),
                        const SizedBox(height: 14),
                        _mainAction(),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                if (_entities.isNotEmpty) ...[
                  const Text('解析实体', style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  ..._entities.map((entity) => Card(
                        child: ListTile(
                          title: Text('${kItemLabel[entity.itemKey]} · ${entity.value} ${entity.unit}'),
                          subtitle: Text('operation: ${entity.operation.name} · conf: ${entity.confidence.toStringAsFixed(2)}'),
                        ),
                      )),
                ],
                const Spacer(),
                ElevatedButton(
                  onPressed: (_state == VoiceState.success || _state == VoiceState.lowConfidence) && !_confirming ? _confirm : null,
                  child: Text(_confirming ? '提交中...' : '确认入库'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _stateBadge() {
    final text = switch (_state) {
      VoiceState.idle => '默认',
      VoiceState.recording => '录音中',
      VoiceState.parsing => '解析中',
      VoiceState.success => '解析成功',
      VoiceState.failure => '解析失败',
      VoiceState.lowConfidence => '低置信度',
    };
    final color = switch (_state) {
      VoiceState.failure => const Color(0xFFC9410A),
      VoiceState.lowConfidence => const Color(0xFFE5BE45),
      VoiceState.success => const Color(0xFF2E8B57),
      _ => Theme.of(context).colorScheme.onSurface.withOpacity(0.54),
    };
    return Text(text, style: TextStyle(color: color, fontWeight: FontWeight.w700));
  }

  Widget _waveView() {
    final active = _state == VoiceState.recording;
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(10, (index) {
        final h = active ? (10 + (index % 4) * 8).toDouble() : 8.0;
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 2),
          width: 6,
          height: h,
          decoration: BoxDecoration(
            color: active ? const Color(0xFFE5BE45) : Theme.of(context).colorScheme.onSurface.withOpacity(0.12),
            borderRadius: BorderRadius.circular(3),
          ),
        );
      }),
    );
  }

  Widget _mainAction() {
    switch (_state) {
      case VoiceState.idle:
      case VoiceState.failure:
        return ElevatedButton.icon(
          onPressed: _startRecording,
          icon: const Icon(Icons.mic_none_rounded),
          label: const Text('开始录音'),
        );
      case VoiceState.recording:
        return ElevatedButton.icon(
          onPressed: _stopRecording,
          icon: const Icon(Icons.stop_circle_outlined),
          label: const Text('结束录音'),
        );
      case VoiceState.parsing:
        return const LinearProgressIndicator();
      case VoiceState.success:
      case VoiceState.lowConfidence:
        return OutlinedButton.icon(
          onPressed: _startRecording,
          icon: const Icon(Icons.replay),
          label: const Text('重录'),
        );
    }
  }
}
