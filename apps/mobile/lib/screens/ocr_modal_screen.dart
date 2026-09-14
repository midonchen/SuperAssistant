import 'package:flutter/material.dart';

import '../core/app_store.dart';
import '../core/models.dart';
import '../routes/app_routes.dart';

enum OcrState { idle, shooting, uploading, parsing, partial, success, failure }

class OcrModalScreen extends StatefulWidget {
  const OcrModalScreen({super.key});

  @override
  State<OcrModalScreen> createState() => _OcrModalScreenState();
}

class _OcrModalScreenState extends State<OcrModalScreen> {
  final store = AppStore.instance;

  OcrState _state = OcrState.idle;
  final List<String> _images = [];
  final List<ParsedEntity> _entities = [];
  List<String> _unknownItems = [];
  String _sessionId = '';
  bool _confirming = false;

  Future<void> _startParse() async {
    setState(() {
      _state = OcrState.shooting;
      _images.clear();
      _entities.clear();
      _unknownItems = [];
      _sessionId = '';
    });

    try {
      await Future<void>.delayed(const Duration(milliseconds: 400));
      if (!mounted) {
        return;
      }
      setState(() {
        _images.addAll(['receipt_01.jpg', 'receipt_02.jpg']);
        _state = OcrState.uploading;
      });

      await Future<void>.delayed(const Duration(milliseconds: 500));
      if (!mounted) {
        return;
      }
      setState(() => _state = OcrState.parsing);

      final result = await store.parseOcr(imageUrls: _images);
      if (!mounted) {
        return;
      }
      _sessionId = result.sessionId;
      _entities
        ..clear()
        ..addAll(result.entities.map((entity) => entity.withSessionId(_sessionId)));
      _unknownItems = result.unknownItems;

      if (_entities.isEmpty && _unknownItems.isEmpty) {
        setState(() => _state = OcrState.failure);
      } else {
        setState(() => _state = _unknownItems.isEmpty ? OcrState.success : OcrState.partial);
      }
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() => _state = OcrState.failure);
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
        source: ActionSource.ocr,
      );
      if (!mounted) {
        return;
      }
      Navigator.pop(context);
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() => _state = OcrState.failure);
    } finally {
      if (mounted) {
        setState(() => _confirming = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('OCR 录入')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('状态：${_state.name}'),
              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          ElevatedButton.icon(
                            onPressed: (_state == OcrState.uploading || _state == OcrState.parsing || _confirming) ? null : _startParse,
                            icon: const Icon(Icons.photo_camera_outlined),
                            label: const Text('拍照并解析'),
                          ),
                          const SizedBox(width: 8),
                          if (_state == OcrState.uploading || _state == OcrState.parsing)
                            const Expanded(child: LinearProgressIndicator()),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text('图片队列：${_images.join(', ')}'),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 10),
              if (_entities.isNotEmpty) ...[
                const Text('解析结果', style: TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 6),
                ..._entities.map((entity) => Card(
                      child: ListTile(
                        title: Text('${kItemLabel[entity.itemKey]} +${entity.value} ${entity.unit}'),
                        subtitle: Text('confidence: ${entity.confidence.toStringAsFixed(2)}'),
                      ),
                    )),
              ],
              if (_unknownItems.isNotEmpty) ...[
                const SizedBox(height: 8),
                Card(
                  child: ListTile(
                    title: Text('未识别项：${_unknownItems.join('、')}'),
                    subtitle: const Text('进入手动补全'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.pushNamed(
                      context,
                      AppRoutes.manualFill,
                      arguments: {'unknownItems': _unknownItems},
                    ),
                  ),
                )
              ],
              const Spacer(),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text('取消'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: (_state == OcrState.success || _state == OcrState.partial) && !_confirming ? _confirm : null,
                      child: Text(_confirming ? '提交中...' : '确认入库'),
                    ),
                  )
                ],
              )
            ],
          ),
        ),
      ),
    );
  }
}
