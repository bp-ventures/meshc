"""Tests for meshc.cli module."""
import pytest

from meshc.cli import build_parser


class TestBuildParser:
    def test_help(self):
        parser = build_parser()
        # Should not raise
        assert parser.prog == "meshc"

    def test_link_token_args(self):
        parser = build_parser()
        args = parser.parse_args([
            "link-token",
            "--user-id", "test",
            "--address", "GADDR",
            "--symbol", "USDC",
        ])
        assert args.user_id == "test"
        assert args.address == "GADDR"
        assert args.symbol == "USDC"

    def test_networks_filter(self):
        parser = build_parser()
        args = parser.parse_args(["networks", "--filter", "stellar"])
        assert args.filter == "stellar"

    def test_mock_deposit_args(self):
        parser = build_parser()
        args = parser.parse_args([
            "mock-deposit",
            "--user-id", "u1",
            "--address", "GADDR",
            "--symbol", "XLM",
            "--amount", "100",
            "--delay", "0.5",
        ])
        assert args.amount == 100.0
        assert args.delay == 0.5
