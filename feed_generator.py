cat > feed_generator.py << 'EOF'
# -----------------------------------------------------------------------------
# NovaZen Feed - WooCommerce to Google Shopping Feed Generator
#
# A robust, high-performance Python script for generating Google
# Shopping-compatible XML product feeds directly from a WooCommerce MySQL
# database, designed for automation and scalability.
# -----------------------------------------------------------------------------

import mysql.connector
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn

# Imports for changing file ownership to solve web server permission issues
import pwd
import grp
# Import for HTML stripping and character unescaping
import html

# --- Configuration Loading ---
def load_config(config_path='config.json'):
    """Loads settings from the JSON config file."""
    try:
        with open(config_path) as f:
            return json.load(f)
    except Exception as e:
        Console().print(f"[bold red]Error loading {config_path}: {e}[/bold red]")
        sys.exit(1)

def load_mapping(mapping_path='feed_mapping.json'):
    """Loads the XML structure definition from the JSON mapping file."""
    try:
        with open(mapping_path) as f:
            return json.load(f)
    except Exception as e:
        Console().print(f"[bold red]Error loading {mapping_path}: {e}[/bold red]")
        sys.exit(1)

# --- Database Operations ---
def get_db_connection(db_config):
    """Establishes a connection to the MySQL database."""
    try:
        connection_args = db_config.copy()
        connection_args.pop('table_prefix', None)
        return mysql.connector.connect(**connection_args)
    except mysql.connector.Error as err:
        Console().print(f"[bold red]Database connection failed: {err}[/bold red]")
        logging.error(f"Database connection failed: {err}")
        sys.exit(1)

def get_total_product_count(connection, table_prefix, limit=0):
    """Gets the total count of products to be processed, filtering for featured images."""
    base_query = f"""
        SELECT COUNT(p.ID) FROM {table_prefix}posts p
        WHERE p.post_status = 'publish' AND (
            (p.post_type = 'product' AND EXISTS (
                SELECT 1 FROM {table_prefix}postmeta pm WHERE pm.post_id = p.ID AND pm.meta_key = '_thumbnail_id'
            )) OR
            (p.post_type = 'product_variation' AND EXISTS (
                SELECT 1 FROM {table_prefix}postmeta pm WHERE pm.post_id = p.post_parent AND pm.meta_key = '_thumbnail_id'
            ))
        )
    """
    cursor = connection.cursor()
    cursor.execute(base_query)
    total = cursor.fetchone()[0]
    cursor.close()
    
    if limit > 0 and total > limit:
        return limit
    return total

def fetch_products(connection, table_prefix, products_per_page, page):
    """Fetches a paginated list of products from the database."""
    offset = page * products_per_page
    query = f"""
        SELECT
            p.ID, p.post_title, p.post_content, p.post_parent, p.guid
        FROM {table_prefix}posts p
        WHERE p.post_status = 'publish' AND (
            (p.post_type = 'product' AND EXISTS (
                SELECT 1 FROM {table_prefix}postmeta pm WHERE pm.post_id = p.ID AND pm.meta_key = '_thumbnail_id'
            )) OR
            (p.post_type = 'product_variation' AND EXISTS (
                SELECT 1 FROM {table_prefix}postmeta pm WHERE pm.post_id = p.post_parent AND pm.meta_key = '_thumbnail_id'
            ))
        )
        ORDER BY p.ID
        LIMIT {products_per_page} OFFSET {offset}
    """
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query)
    return cursor.fetchall()

def get_product_meta(connection, product_id, table_prefix):
    """Fetches all post meta for a given product ID into a dictionary."""
    query = f"SELECT meta_key, meta_value FROM {table_prefix}postmeta WHERE post_id = %s"
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, (product_id,))
    return {row['meta_key']: row['meta_value'] for row in cursor.fetchall()}

def get_image_url(connection, thumbnail_id, table_prefix):
    """Fetches the URL for a given attachment ID."""
    if not thumbnail_id: return ""
    query = f"SELECT guid FROM {table_prefix}posts WHERE ID = %s"
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, (thumbnail_id,))
    result = cursor.fetchone()
    return result['guid'] if result else ""

def get_additional_image_urls(connection, product_id, table_prefix, limit=3):
    """Fetches URLs for the product's gallery images."""
    meta = get_product_meta(connection, product_id, table_prefix)
    gallery_ids_str = meta.get('_product_image_gallery')
    if not gallery_ids_str: return []
    gallery_ids = [int(id) for id in gallery_ids_str.split(',') if id.isdigit()]
    if not gallery_ids: return []
    limited_ids = gallery_ids[:limit]
    placeholders = ','.join(['%s'] * len(limited_ids))
    query = f"SELECT guid FROM {table_prefix}posts WHERE ID IN ({placeholders}) ORDER BY menu_order ASC"
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, tuple(limited_ids))
    return [row['guid'] for row in cursor.fetchall()]

def get_category_path(connection, product_id, table_prefix):
    """Fetches the primary product category."""
    query = f"""
        SELECT t.name FROM {table_prefix}term_relationships tr
        JOIN {table_prefix}term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
        JOIN {table_prefix}terms t ON tt.term_id = t.term_id
        WHERE tr.object_id = %s AND tt.taxonomy = 'product_cat'
        ORDER BY tr.term_order LIMIT 1
    """
    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, (product_id,))
    result = cursor.fetchone()
    return result['name'] if result else ""
    
# --- XML Generation for Streaming ---
def write_xml_header(feed_file, config):
    """Writes the opening tags of the XML file."""
    feed_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    feed_file.write('<rss xmlns:g="http://base.google.com/ns/1.0" version="2.0">\n')
    feed_file.write('  <channel>\n')
    feed_file.write(f"    <title>SemiNest.in</title>\n")
    feed_file.write(f"    <link>{config['store_details']['domain']}</link>\n")
    feed_file.write("    <description>Product feed for Google Shopping</description>\n")

def write_xml_footer(feed_file):
    """Writes the closing tags of the XML file."""
    feed_file.write('  </channel>\n')
    feed_file.write('</rss>\n')

def write_item_xml(product_data, mapping, regional_config):
    """Generates the XML string for a single <item>, including regional tags."""
    item_element = Element('item')
    for key, details in mapping.items():
        source = details.get("source")
        value = product_data.get(key)
        
        if source == "regional:shipping":
            shipping_element = SubElement(item_element, details['xml_tag'])
            SubElement(shipping_element, "g:country").text = regional_config.get('country')
            SubElement(shipping_element, "g:service").text = regional_config['shipping'].get('service')
            price_element = SubElement(shipping_element, "g:price")
            price_element.text = f"{regional_config['shipping'].get('price')} {regional_config.get('currency')}"
            continue
        
        if source == "regional:tax":
            tax_element = SubElement(item_element, details['xml_tag'])
            SubElement(tax_element, "g:country").text = regional_config.get('country')
            SubElement(tax_element, "g:rate").text = regional_config['tax'].get('rate')
            SubElement(tax_element, "g:tax_ship").text = "n"
            continue

        if value is not None and str(value) != '':
            xml_tag = details['xml_tag']
            if 'value_map' in details and value in details['value_map']:
                value = details['value_map'][value]
            if 'suffix' in details and value:
                value = str(value) + details.get('suffix', '')
            
            sub_element = SubElement(item_element, xml_tag)
            sub_element.text = str(value)

    xml_string = tostring(item_element, 'unicode', short_empty_elements=False)
    return "    " + xml_string.replace("\n", "\n    ") + "\n"

# --- Main Application Logic ---
def main():
    console = Console()
    start_time = datetime.now()
    
    config = load_config()
    mapping = load_mapping()
    
    server_load_config = config.get('server_load_reduction', {})
    reduce_load = server_load_config.get('enabled', False)
    pause_duration = server_load_config.get('pause_seconds_per_chunk', 2)

    test_run_config = config.get('test_run', {})
    test_mode_enabled = test_run_config.get('enabled', False)
    product_limit = test_run_config.get('product_limit', 0) if test_mode_enabled else 0

    regional_config = config.get('regional_settings', {})

    log_file = config['feed_settings']['log_file']
    logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    console.print("[bold cyan]--- Starting NovaZen Feed Generation ---[/bold cyan]")
    if test_mode_enabled:
        console.print(f"[bold yellow]Running in TEST MODE: Limited to {product_limit} products.[/bold yellow]")
    logging.info("--- Starting Feed Generation ---")

    connection = get_db_connection(config['database'])
    
    console.print("Getting total product count...")
    total_products = get_total_product_count(connection, config['database']['table_prefix'], product_limit)

    if total_products == 0:
        console.print("[yellow]Warning: No products found to process.[/yellow]")
        connection.close()
        return

    console.print(f"Found [bold green]{total_products}[/bold green] products to process.")

    processed_count = 0
    skipped_count = 0
    page = 0
    output_file_path = config['feed_settings']['output_file']

    try:
        with open(output_file_path, 'w', encoding='utf-8') as feed_file:
            write_xml_header(feed_file, config)

            progress_bar = Progress(
                TextColumn("[progress.description]{task.description}"), BarColumn(),
                MofNCompleteColumn(), TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                TimeRemainingColumn(), TimeElapsedColumn(), console=console, disable=not console.is_terminal
            )

            with progress_bar as progress:
                fetch_task = progress.add_task("[green]Processing products...", total=total_products)

                while processed_count < total_products:
                    products_to_fetch = config['feed_settings']['products_per_page']
                    if product_limit > 0:
                        if (processed_count + products_to_fetch) > product_limit:
                            products_to_fetch = product_limit - processed_count

                    products = fetch_products(connection, config['database']['table_prefix'], products_to_fetch, page)
                    if not products:
                        break

                    for product in products:
                        if product_limit > 0 and processed_count >= product_limit:
                            break
                        try:
                            product_data = {}
                            meta = get_product_meta(connection, product['ID'], config['database']['table_prefix'])
                            
                            additional_images = get_additional_image_urls(connection, product['ID'], config['database']['table_prefix'], limit=3)
                            for i, img_url in enumerate(additional_images):
                                product_data[f'additional_image_link_{i+1}'] = img_url

                            for key, details in mapping.items():
                                source = details.get("source")
                                if source and (source.startswith("regional:") or source.startswith("additional_image")):
                                    continue
                                
                                value = None
                                if source == "ID": value = product['ID']
                                elif source == "guid": value = product['guid']
                                elif source in ['post_title', 'post_content']: 
                                    value = product[source]
                                    # *** NEW: Truncate description to 350 chars ***
                                    if source == 'post_content' and value:
                                        # First, clean HTML tags and unescape characters
                                        clean_value = html.unescape(value.strip())
                                        # A simple regex to strip remaining shortcodes and tags
                                        import re
                                        clean_value = re.sub('<[^<]+?>', '', clean_value)
                                        clean_value = re.sub(r'\[.*?\]', '', clean_value)
                                        if len(clean_value) > 350:
                                            value = clean_value[:347] + "..."
                                        else:
                                            value = clean_value

                                elif source.startswith("_"): value = meta.get(source)
                                elif source == "thumbnail_url": value = get_image_url(connection, meta.get('_thumbnail_id'), config['database']['table_prefix'])
                                elif source == "category_path":
                                    parent_id = product['post_parent'] if product['post_parent'] != 0 else product['ID']
                                    value = get_category_path(connection, parent_id, config['database']['table_prefix'])
                                elif source == "fixed": value = details.get("value")
                                
                                product_data[key] = value
                            
                            item_xml = write_item_xml(product_data, mapping, regional_config)
                            feed_file.write(item_xml)
                            
                        except Exception as e:
                            logging.error(f"Failed to process product ID {product.get('ID', 'N/A')}: {e}", exc_info=True)
                            skipped_count += 1
                        
                        progress.update(fetch_task, advance=1)
                        processed_count += 1
                    
                    if product_limit > 0 and processed_count >= product_limit:
                        break
                    
                    if not console.is_terminal:
                        percentage = (processed_count / total_products) * 100
                        console.print(f"Progress: {processed_count}/{total_products} ({percentage:.1f}%) processed.")

                    page += 1

                    if reduce_load:
                        if console.is_terminal:
                            progress.log(f"[dim]Pausing for {pause_duration} seconds...[/dim]")
                        else:
                            console.print(f"Pausing for {pause_duration} seconds to reduce server load...")
                        time.sleep(pause_duration)

            write_xml_footer(feed_file)
            
    except Exception as e:
        console.print(f"[bold red]A critical error occurred: {e}[/bold red]")
        logging.error(f"An error occurred during file generation: {e}", exc_info=True)
    
    try:
        web_user = 'www-data'
        uid = pwd.getpwnam(web_user).pw_uid
        gid = grp.getgrnam(web_user).gr_gid
        os.chown(output_file_path, uid, gid)
        os.chmod(output_file_path, 0o664)
        console.print(f"Permissions for [cyan]{output_file_path}[/cyan] set for web server.")
        logging.info(f"Set permissions for {output_file_path} to {web_user}:{web_user}.")
    except (KeyError, OSError) as e:
        console.print(f"[yellow]Warning: Could not change file ownership to 'www-data'. {e}[/yellow]")
        logging.warning(f"Could not change ownership for {output_file_path}: {e}")

    console.print(f"[bold green]✔ Feed generation complete.[/bold green]")
    connection.close()
    
    console.print("\n[bold cyan]--- NovaZen Feed Summary ---[/bold cyan]")
    end_time = datetime.now()
    duration = end_time - start_time
    console.print(f"Total products processed: [bold green]{processed_count}[/bold green]")
    if skipped_count > 0:
        console.print(f"Total products skipped: [bold red]{skipped_count}[/bold red] (see {log_file} for details)")
    console.print(f"Duration: [bold cyan]{duration}[/bold cyan]")
    
if __name__ == "__main__":
    os.makedirs('logs', exist_ok=True)
    main()
EOF
