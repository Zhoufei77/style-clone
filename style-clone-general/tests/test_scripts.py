"""Offline regressions for corpus preservation, privacy, and stable metrics."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import preprocess as PRE
import distill_metrics as MET


def run_script(name, *args):
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, "-B", str(SCRIPTS / name), *map(str, args)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment)


class PreprocessTests(unittest.TestCase):
    def test_real_srt_keeps_words_and_original_punctuation(self):
        text = "1\n00:00:01,200 --> 00:00:03,000\n你好，世界！\n\n2\n00:00:03,100 --> 00:00:05,000\n他说：‘先保存文件。’\n这是字幕的第二行。\n"
        clean = PRE.clean_text(text, "transcript")
        self.assertEqual(clean, "你好，世界！\n他说：‘先保存文件。’\n这是字幕的第二行。")
        self.assertNotIn("-->", clean)
        self.assertNotIn("\n\n", clean)

    def test_real_webvtt_hides_cue_scaffolding_but_keeps_text(self):
        text = "WEBVTT\nKind: captions\nLanguage: zh\n\nNOTE editor note\n不要计入正文\n\nSTYLE\n::cue { color: red }\n\ncue-one\n00:01.000 --> 00:03.100 align:start\n<v 张三><c.green>文字 &amp; 数字。</c></v>\n\ncue-two\n00:03.200 --> 00:04.000\n<00:03.300>关键词：请保留这句话。\n"
        clean = PRE.clean_text(text, "transcript")
        self.assertEqual(clean, "文字 & 数字。\n关键词：请保留这句话。")

    def test_timestamped_transcript_retains_heading_quotation_and_keyword_sentence(self):
        text = "# 正文标题\n文字记录\n说话人 1 00:00:01\n> 引用原话，不能删除。\n关键词决定文章能否被找到。\n说话人 2 00:00:04 关键词：这是实际说的话。\n[00:00:06] 最后一段还在。"
        clean = PRE.clean_text(text, "transcript")
        for expected in ("正文标题", "引用原话，不能删除。", "关键词决定文章能否被找到。", "关键词：这是实际说的话。", "最后一段还在。"):
            self.assertIn(expected, clean)
        self.assertNotIn("00:00", clean)
        self.assertNotIn("说话人 1", clean)

    def test_auto_does_not_treat_keyword_prose_as_a_transcript(self):
        text = "关键词决定检索结果。\n\n文字记录也可以成为小说标题。\n\n12:00 开会，这是当天的安排。"
        mode = PRE.choose_mode(text, Path("普通文章.txt"))
        self.assertEqual(mode, "plain")
        self.assertEqual(PRE.clean_text(text, mode), text)

    def test_html_preserves_paragraphs_entities_and_headings_without_scripts(self):
        text = "<!DOCTYPE html><html><head><title>网页元信息</title><style>隐藏内容</style></head><body><h1>正文标题</h1><p>甲 &amp; 乙，价格&#58; 12。</p><p>第二段<br>换行 &lt; 示例。</p><script>隐藏脚本();</script><blockquote>引用原话。</blockquote></body></html>"
        clean = PRE.clean_text(text, "html")
        self.assertEqual(clean, "正文标题\n\n甲 & 乙，价格: 12。\n\n第二段\n换行 < 示例。\n\n引用原话。")
        self.assertNotIn("隐藏", clean)
        self.assertNotIn("元信息", clean)

    def test_markdown_keeps_visible_headings_quotes_links_and_code_terms(self):
        text = "---\nlayout: post\n---\n# 正文标题\n\n> 一句原话：保持准确。\n\n关键词：保留真实句子。\n\n这里有**强调**、[链接正文](https://example.test)和`Python`。\n\n~~~python\n非正文代码()\n~~~\n"
        clean = PRE.clean_text(text, "markdown")
        self.assertIn("正文标题", clean)
        self.assertIn("一句原话：保持准确。", clean)
        self.assertIn("关键词：保留真实句子。", clean)
        self.assertIn("这里有强调、链接正文和Python。", clean)
        self.assertNotIn("非正文代码", clean)
        self.assertNotIn("layout", clean)

    def test_speech_normalization_requires_flag_and_records_measurement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "稿件.txt"
            source.write_text("逗号，分号；冒号：感叹！疑问？原句。", encoding="utf-8")
            original = PRE.prepare([source], root / "original")
            speech = PRE.prepare([source], root / "speech", speech_units=True)
            self.assertEqual(original["punctuation"], "original")
            self.assertIn("，", (root / "original" / "D001.txt").read_text(encoding="utf-8"))
            self.assertEqual(speech["punctuation"], "speech_units")
            self.assertEqual((root / "speech" / "D001.txt").read_text(encoding="utf-8"), "逗号。分号。冒号。感叹。疑问。原句。\n")

    def test_duplicate_basenames_bom_crlf_and_sources_are_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first, second = root / "甲" / "同名.txt", root / "乙" / "同名.md"
            first.parent.mkdir()
            second.parent.mkdir()
            first.write_bytes(b"\xef\xbb\xbf" + "第一篇，原文。\r\n第二行。".encode("utf-8"))
            second.write_text("# 第二篇标题\n\n第二篇正文。", encoding="utf-8")
            before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (first, second)}
            manifest = PRE.prepare([root], root / "output")
            self.assertEqual(len(manifest["documents"]), 2)
            self.assertEqual({item["output"] for item in manifest["documents"]}, {"D001.txt", "D002.txt"})
            self.assertEqual(before, {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (first, second)})
            for record in manifest["documents"]:
                self.assertNotIn("\r", (root / "output" / record["output"]).read_text(encoding="utf-8"))
            self.assertNotIn(str(root), json.dumps(manifest, ensure_ascii=False))

    def test_nested_output_hidden_and_symbolic_paths_are_excluded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "正文.txt").write_text("这是一篇正文。", encoding="utf-8")
            (root / ".hidden").mkdir()
            (root / ".hidden" / "secret.txt").write_text("隐藏正文。", encoding="utf-8")
            output = root / "prepared"
            PRE.prepare([root], output)
            try:
                (root / "link.txt").symlink_to(root / "正文.txt")
            except (OSError, NotImplementedError):
                pass
            second = PRE.prepare([root], output, overwrite=True)
            self.assertEqual(len(second["documents"]), 1)
            self.assertEqual(second["documents"][0]["source_name"], "正文.txt")

    def test_existing_output_is_not_overwritten_by_default(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "input.txt"
            source.write_text("真实语料正文。", encoding="utf-8")
            PRE.prepare([source], root / "output")
            target = root / "output" / "D001.txt"
            before = target.read_bytes()
            with self.assertRaises(ValueError):
                PRE.prepare([source], root / "output")
            self.assertEqual(target.read_bytes(), before)

    def test_decode_failure_prevents_partial_success_and_returns_two(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a.txt").write_text("有效的正文。", encoding="utf-8")
            (root / "b.txt").write_bytes(b"\xff\xfe\x00")
            result = run_script("preprocess.py", root, "--out", root / "output")
            self.assertEqual(result.returncode, 2)
            self.assertFalse((root / "output").exists())
            (root / "b.txt").unlink()
            (root / "a.txt").unlink()
            self.assertEqual(run_script("preprocess.py", root, "--out", root / "output").returncode, 2)


class MetricsTests(unittest.TestCase):
    def test_distributions_known_quantiles_and_cv(self):
        result = MET.distribution([1, 2, 3, 4])
        self.assertEqual(result["mean"], 2.5)
        self.assertEqual(result["median"], 2.5)
        self.assertEqual(result["p25"], 1.75)
        self.assertEqual(result["p90"], 3.7)
        self.assertAlmostEqual(result["cv_population"], 0.447214)

    def test_empty_data_uses_null_and_na_without_division_errors(self):
        report = MET.analyze_documents([])
        self.assertEqual(report["document_count"], 0)
        self.assertIsNone(report["summary"]["sentences"]["mean"])
        self.assertIsNone(report["summary"]["sentences"]["cv_population"])
        self.assertIsNone(report["summary"]["sentence_ratios"]["le_8"])
        self.assertIsNone(report["summary"]["per_1000_length_units"]["digits"])
        self.assertIn("N/A", MET.render_report(report))
        self.assertNotIn("NaN", json.dumps(report, allow_nan=False))
        empty_file = MET.analyze_documents([("", "plain")])
        self.assertEqual(empty_file["documents"][0]["status"], "empty")

    def test_summary_pools_sentences_instead_of_averaging_document_means(self):
        report = MET.analyze_documents([("甲。", "plain"), ("乙丙丁戊。己庚辛壬。", "plain")])
        self.assertEqual(report["summary"]["sentences"]["mean"], 3)
        self.assertEqual(report["summary"]["sentences"]["n"], 3)
        self.assertEqual([item["label"] for item in report["documents"]], ["D001", "D002"])

    def test_literals_particles_rhetoric_numbers_english_and_punctuation(self):
        report = MET.analyze_documents([("他问：“可以吧？”\n\n不过，这不是甲，而是乙。甲、乙、丙。Python 3.14，2026年。", "plain")])
        metrics = report["summary"]
        self.assertEqual(metrics["particle_sentence_endings"], 1)
        self.assertEqual(metrics["transitions"]["不过"], 1)
        self.assertEqual(metrics["rhetorical_patterns"]["not_but"], 1)
        self.assertEqual(metrics["rhetorical_patterns"]["three_item_enumeration"], 1)
        self.assertEqual(metrics["numeric_english"]["number_blocks"], 2)
        self.assertEqual(metrics["numeric_english"]["english_blocks"], 1)
        self.assertEqual(metrics["punctuation"]["？"], 1)

    def test_html_and_markdown_layout_markers_remain_counted(self):
        report = MET.analyze_documents([
            ("# 标题\n\n**加粗正文**\n\n> 引语。\n\n![图](x.png)\n\n- 条目。", "markdown"),
            ("<h2>标题</h2><p><strong>正文</strong></p><img src='x'><blockquote>引文。</blockquote><ul><li>条目。</li></ul><script>window.x='<img>'</script>", "html"),
        ])
        layout = report["summary"]["layout"]
        self.assertEqual(layout["headings"], 2)
        self.assertEqual(layout["markdown_bold"], 1)
        self.assertEqual(layout["html_bold"], 1)
        self.assertEqual(layout["images"], 2)
        self.assertEqual(layout["quote_blocks"], 2)
        self.assertEqual(layout["list_items"], 2)

    def test_indented_long_fence_keeps_fake_layout_out_of_baseline(self):
        raw = "  ````python\n# 伪标题\n**伪加粗**\n```\n# 短围栏尚未关闭代码\n  ````\n\n# 真实标题\n\n正文保留。"
        report = MET.analyze_documents([(raw, "markdown")])
        self.assertEqual(report["summary"]["layout"]["headings"], 1)
        self.assertEqual(report["summary"]["layout"]["markdown_bold"], 0)
        self.assertNotIn("伪标题", PRE.clean_text(raw, "markdown"))

    def test_default_reports_do_not_leak_raw_text_filenames_or_absolute_paths(self):
        secret = "阿尔法秘密客户来访。"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            corpus = root / "private-corpus"
            corpus.mkdir()
            (corpus / "保密客户阿尔法.txt").write_text(secret, encoding="utf-8")
            out, machine = corpus / "report.md", corpus / "report.json"
            first = MET.build_report(corpus, out, machine)
            for content in (out.read_text(encoding="utf-8"), machine.read_text(encoding="utf-8")):
                self.assertNotIn(secret, content)
                self.assertNotIn("阿尔法", content)
                self.assertNotIn(str(root), content)
                self.assertNotIn("private-corpus", content)
                self.assertNotIn("保密客户", content)
            second = MET.build_report(corpus, out, machine, overwrite=True)
            self.assertEqual(first, second)
            self.assertEqual(second["document_count"], 1)
            explicit = MET.analyze_documents([(secret, "plain")], include_samples=True)
            self.assertIn("阿尔法", json.dumps(explicit, ensure_ascii=False))

    def test_old_generated_reports_are_not_reingested_with_a_new_output_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "source.txt").write_text("这是一份实际语料。", encoding="utf-8")
            MET.build_report(root, root / "first.md")
            report = MET.build_report(root, root / "second.md")
            self.assertEqual(report["document_count"], 1)

    def test_output_never_overwrites_corpus_source_even_with_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "essay.md"
            source.write_text("一份需要保留的语料。", encoding="utf-8")
            original = source.read_bytes()
            with self.assertRaises(ValueError):
                MET.build_report(root, source, overwrite=True)
            with self.assertRaises(ValueError):
                MET.build_report(source, source, overwrite=True)
            self.assertEqual(source.read_bytes(), original)

    def test_file_cli_is_deterministic_and_failure_returns_two(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "中文 空格.md"
            source.write_bytes(b"\xef\xbb\xbf" + "# 一份标题\r\n\r\n这里是正文，价格12元。".encode("utf-8"))
            before = source.read_bytes()
            for suffix in ("one", "two"):
                result = run_script("distill_metrics.py", source, "--out", root / (suffix + ".md"), "--json", root / (suffix + ".json"))
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / "one.md").read_bytes(), (root / "two.md").read_bytes())
            self.assertEqual((root / "one.json").read_bytes(), (root / "two.json").read_bytes())
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(run_script("distill_metrics.py", source, "--out", root / "one.md").returncode, 2)
            self.assertEqual(run_script("distill_metrics.py", root / "missing", "--out", root / "missing.md").returncode, 2)


if __name__ == "__main__":
    unittest.main()
