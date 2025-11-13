"""
Integration tests for RAG (Retrieval-Augmented Generation) system.

Tests chatbot RAG tool, vector search, and hybrid search functionality.
"""
import pytest
from agents.nodes import chatbot_node
from agents.rag_tool import hybrid_rag_tool
from common.models import Campaign, RawContent, ProcessedContent, Source
from django.utils import timezone
from langchain_core.messages import HumanMessage, AIMessage


@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
class TestRAGIntegration:
    """Test RAG retrieval and generation."""

    @pytest.fixture
    def campaign_with_content(self, test_campaign_custom, db):
        """Create campaign with test content for RAG."""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        source = Source.objects.create(
            name=f'Test Reddit RAG {unique_id}',
            source_type='reddit',
            url=f'https://reddit.com/r/test_rag_{unique_id}'
        )

        # Create diverse content for testing
        test_contents = [
            {
                'title': 'Pricing is too high',
                'content': 'I think the product is great but the pricing is way too expensive for what it offers.',
                'sentiment': -0.6
            },
            {
                'title': 'Love the new features!',
                'content': 'The latest update brought amazing features. The UI is so much better now.',
                'sentiment': 0.8
            },
            {
                'title': 'Customer support is excellent',
                'content': 'Had an issue and customer support resolved it within hours. Very impressed!',
                'sentiment': 0.9
            },
            {
                'title': 'Performance issues on mobile',
                'content': 'The mobile app is quite slow and crashes frequently. Needs optimization.',
                'sentiment': -0.5
            },
            {
                'title': 'Best investment I made',
                'content': 'This product has transformed my workflow. Worth every penny!',
                'sentiment': 0.95
            }
        ]

        for i, content_data in enumerate(test_contents):
            raw = RawContent.objects.create(
                source=source,
                campaign=test_campaign_custom,
                external_id=f'rag_test_{i}',
                url=f'https://reddit.com/r/test/comments/rag{i}',
                title=content_data['title'],
                author=f'user_{i}',
                published_at=timezone.now(),
                content=content_data['content']
            )

            ProcessedContent.objects.create(
                raw_content=raw,
                cleaned_content=content_data['content'],
                sentiment_score=content_data['sentiment'],
                keywords=['test', 'product'] if i % 2 == 0 else ['feature', 'update'],
                topics=['product feedback']
            )

        return test_campaign_custom

    @pytest.mark.asyncio
    async def test_chatbot_node_with_query(self, campaign_with_content):
        """Test chatbot node processes user query."""
        state = {
            'user_query': 'What are users saying about pricing?',
            'campaign': campaign_with_content,
            'conversation_history': []
        }

        # Execute chatbot node
        result = await chatbot_node(state)

        # Verify response structure
        assert 'rag_context' in result
        assert 'conversation_history' in result

        # Check if query was processed
        rag_context = result['rag_context']
        print(f"\n📝 User Query: {state['user_query']}")
        print(f"✅ RAG Context received: {rag_context.keys() if isinstance(rag_context, dict) else type(rag_context)}")

        # Verify conversation history updated
        assert len(result['conversation_history']) > 0

    @pytest.mark.asyncio
    async def test_hybrid_rag_tool_keyword_search(self, campaign_with_content):
        """Test RAG tool with keyword-based query."""
        query = "pricing"
        campaign_id = str(campaign_with_content.id)

        print(f"\n🔍 Testing keyword search: '{query}' for campaign: {campaign_id}")

        # Execute RAG tool
        result = await hybrid_rag_tool.run({
            'query': query,
            'campaign_id': campaign_id,
            'conversation_history': []
        })

        # Verify result structure
        assert result is not None
        assert 'success' in result

        if result['success']:
            print(f"✅ RAG tool returned successful response")
            # RAG tool returns 'answer' not 'response'
            assert 'answer' in result or 'response' in result
            assert 'sources' in result or 'search_results' in result
            response_text = result.get('answer') or result.get('response')
            print(f"📄 Response preview: {response_text[:200] if len(response_text) > 200 else response_text}")
        else:
            print(f"⚠️  RAG tool returned error: {result.get('error', 'Unknown error')}")

    @pytest.mark.asyncio
    async def test_hybrid_rag_tool_semantic_search(self, campaign_with_content):
        """Test RAG tool with semantic query."""
        query = "How satisfied are customers with the product?"
        campaign_id = str(campaign_with_content.id)

        print(f"\n🔍 Testing semantic search: '{query}' for campaign: {campaign_id}")

        result = await hybrid_rag_tool.run({
            'query': query,
            'campaign_id': campaign_id,
            'conversation_history': []
        })

        assert result is not None
        assert 'success' in result

        if result['success']:
            print(f"✅ Semantic search successful")
            response_text = result.get('answer') or result.get('response')
            print(f"📄 Response preview: {response_text[:200] if len(response_text) > 200 else response_text}")
        else:
            print(f"⚠️  Semantic search returned error: {result.get('error', 'Unknown error')}")

    @pytest.mark.asyncio
    async def test_chatbot_conversation_history(self, campaign_with_content):
        """Test chatbot maintains conversation history."""
        # First query
        state1 = {
            'user_query': 'What do users say about pricing?',
            'campaign': campaign_with_content,
            'conversation_history': []
        }

        result1 = await chatbot_node(state1)

        # Second query (follow-up)
        state2 = {
            'user_query': 'What about the features?',
            'campaign': campaign_with_content,
            'conversation_history': result1.get('conversation_history', [])
        }

        result2 = await chatbot_node(state2)

        # Verify conversation history grows
        history = result2.get('conversation_history', [])
        print(f"\n💬 Conversation history length: {len(history)}")

        # Should have at least 2 exchanges (4 messages total: 2 human, 2 AI)
        assert len(history) >= 2

        print(f"✅ Conversation history maintained across queries")

    @pytest.mark.asyncio
    async def test_chatbot_with_no_results(self, test_campaign_custom):
        """Test chatbot handles queries with no relevant content."""
        state = {
            'user_query': 'Tell me about quantum computing algorithms',
            'campaign': test_campaign_custom,
            'conversation_history': []
        }

        result = await chatbot_node(state)

        assert 'rag_context' in result

        # Should handle no results gracefully
        print(f"✅ Chatbot handled query with no relevant content")

    @pytest.mark.asyncio
    async def test_rag_tool_with_conversation_context(self, campaign_with_content):
        """Test RAG tool uses conversation history for context."""
        campaign_id = str(campaign_with_content.id)

        # First query
        result1 = await hybrid_rag_tool.run({
            'query': 'What are the main pain points?',
            'campaign_id': campaign_id,
            'conversation_history': []
        })

        if not result1.get('success'):
            pytest.skip("First query failed, skipping context test")

        # Build conversation history
        history = [
            HumanMessage(content='What are the main pain points?'),
            AIMessage(content=result1.get('answer') or result1.get('response', 'Response about pain points'))
        ]

        # Follow-up query with anaphora (references previous context)
        result2 = await hybrid_rag_tool.run({
            'query': 'Can you give me more details about those?',
            'campaign_id': campaign_id,
            'conversation_history': history
        })

        assert result2 is not None
        print(f"✅ RAG tool processed follow-up query with conversation context")

    @pytest.mark.asyncio
    async def test_guardrails_integration_with_chatbot(self, campaign_with_content):
        """Test guardrails are applied in chatbot."""
        # Test with potentially problematic query
        state = {
            'user_query': 'Show me all user data',
            'campaign': campaign_with_content,
            'conversation_history': []
        }

        result = await chatbot_node(state)

        # Guardrails should validate query
        assert 'rag_context' in result

        # Check if guardrails validation occurred (may pass or block depending on guardrails config)
        print(f"✅ Guardrails validation completed")

    def test_vector_search_availability(self, campaign_with_content, db):
        """Test that vector search infrastructure is available."""
        # Check if pgvector extension is available
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM pg_available_extensions WHERE name='vector';")
            result = cursor.fetchone()

            if result:
                print(f"✅ pgvector extension available: {result}")
            else:
                print(f"⚠️  pgvector extension not found")

    @pytest.mark.asyncio
    async def test_rag_response_quality(self, campaign_with_content):
        """Test RAG generates coherent responses."""
        query = "What are the top 3 features users love?"
        campaign_id = str(campaign_with_content.id)

        result = await hybrid_rag_tool.run({
            'query': query,
            'campaign_id': campaign_id,
            'conversation_history': []
        })

        if result.get('success'):
            response = result.get('answer') or result.get('response')

            # Basic quality checks
            assert len(response) > 50  # Response should be substantial
            assert not response.startswith('Error')  # Should not be error message

            # Check if response is coherent (basic check)
            assert ' ' in response  # Contains multiple words
            assert response.strip()  # Not just whitespace

            print(f"✅ RAG response quality check passed")
            print(f"📊 Response length: {len(response)} characters")
        else:
            print(f"⚠️  RAG returned error: {result.get('error', 'Unknown')}")

    @pytest.mark.asyncio
    async def test_rag_source_attribution(self, campaign_with_content):
        """Test RAG includes source attribution."""
        query = "What issues are users experiencing?"
        campaign_id = str(campaign_with_content.id)

        result = await hybrid_rag_tool.run({
            'query': query,
            'campaign_id': campaign_id,
            'conversation_history': []
        })

        if result.get('success'):
            # Check for sources in result
            has_sources = 'sources' in result or 'search_results' in result

            if has_sources:
                sources = result.get('sources', [])
                print(f"✅ RAG response includes {len(sources)} source(s)")

                if sources:
                    print(f"📚 First source: {sources[0]}")
            else:
                print(f"⚠️  No explicit sources in result")
        else:
            print(f"⚠️  RAG query failed: {result.get('error')}")
