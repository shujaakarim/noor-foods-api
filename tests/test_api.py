import unittest
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from noor_foods_api.database import get_session
from noor_foods_api.main import app


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_session] = lambda: object()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()

    def test_missing_category_returns_404(self) -> None:
        with patch(
            "noor_foods_api.routers.categories.crud.get_category",
            return_value=None,
        ):
            response = self.client.get("/categories/99")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Category not found"})

    def test_product_filters_are_forwarded(self) -> None:
        with patch(
            "noor_foods_api.routers.products.crud.list_products",
            return_value=[],
        ) as list_products:
            response = self.client.get(
                "/products?category_id=4&in_stock=true&max_price=150"
                "&limit=3&offset=2"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list_products.call_args.kwargs,
            {
                "category_id": 4,
                "search": None,
                "in_stock": True,
                "max_price": Decimal("150"),
                "limit": 3,
                "offset": 2,
            },
        )

    def test_missing_product_returns_404(self) -> None:
        with patch(
            "noor_foods_api.dependencies.crud.get_product",
            return_value=None,
        ):
            response = self.client.get("/products/9999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Product not found"})

    def test_integrity_error_returns_safe_409(self) -> None:
        with patch(
            "noor_foods_api.routers.products.crud.create_product",
            side_effect=IntegrityError(
                "insert", {}, Exception("internal database detail")
            ),
        ):
            response = self.client.post(
                "/products",
                json={
                    "sku": "ABC",
                    "name": "Product",
                    "category_id": 1,
                    "supplier_id": 1,
                    "unit_price": "1.00",
                },
            )

        self.assertEqual(response.status_code, 409)
        self.assertNotIn("internal database detail", response.text)
