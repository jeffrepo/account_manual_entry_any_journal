# Asientos manuales en cualquier diario — Odoo 19

Nombre técnico: `account_manual_entry_any_journal`  
Versión: `19.0.1.0.0`  
Dependencia: Contabilidad (`account`). Destino: Odoo.sh o servidor propio.

## Funcionamiento

En **Contabilidad → Contabilidad → Asientos contables → Nuevo**, permite elegir
diarios activos de cualquier tipo: Varios, Ventas, Compras, Banco, Efectivo y
Tarjeta de crédito. También admite tipos añadidos por otros módulos.

El cambio aplica a movimientos de tipo asiento (`move_type = 'entry') sin vínculo
a un pago ni a una línea de extracto, y fuera de los contextos de creación de
pagos y extractos. Odoo no tiene un indicador universal que distinga todos los
asientos escritos por una persona de todos los generados por módulos: otros
asientos de tipo `entry` sin esos vínculos también tendrán la selección ampliada.

- Conserva el diario inicial que elegiría Odoo, normalmente uno de tipo Varios.
  Sigue siendo necesario configurar ese diario para crear un asiento sin indicar
  previamente otro diario.
- Conserva el diario elegido al recalcular, guardar y publicar el asiento.
- Mantiene el filtro nativo de compañías y sucursales, los permisos de acceso y
  la exclusión habitual de diarios archivados.
- Facturas, notas de crédito y recibos mantienen sus tipos de diario habituales.
- Conserva las validaciones contables, fechas de bloqueo, numeración y protección
  de asientos publicados de Odoo.

Un asiento manual en Ventas o Compras sigue siendo un asiento: no crea una factura
ni un documento electrónico. Elegir Banco no crea por sí mismo un pago ni una
transacción de extracto. El asiento sí afecta las cuentas y el diario elegidos y
utiliza las reglas de numeración de Odoo para ese diario.

## Instalación en Odoo.sh

El repositorio contiene directamente los archivos del módulo en su raíz:
`__manifest__.py`, `__init__.py`, `models/` y `tests/`. No tiene una segunda
carpeta contenedora llamada `account_manual_entry_any_journal`.

1. Añadir este repositorio como submódulo del proyecto Odoo.sh en una carpeta
   llamada `account_manual_entry_any_journal`, junto a los demás módulos
   personalizados. Como alternativa, copiar los archivos a una carpeta con ese
   nombre en el repositorio principal. Si se utiliza el ZIP, descomprimirlo y
   copiar su carpeta del módulo. En todos los casos, `__manifest__.py` debe quedar
   directamente dentro de la carpeta del módulo que Odoo descubrirá.
2. Enviar el cambio a una rama de desarrollo y esperar que termine la compilación.
3. En la base de esa rama, activar el modo desarrollador, ir a **Aplicaciones →
   Actualizar lista de aplicaciones**, quitar el filtro predeterminado de
   aplicaciones y buscar el nombre técnico. Instalar el módulo.
4. Validar también en una rama de pruebas (staging) con copia de los datos reales
   y los módulos de localización de la empresa.
5. Tras validar los casos siguientes, pasar el cambio a producción e instalar allí
   el módulo. El cambio no necesita migrar ni modificar asientos existentes.

## Comprobación funcional

- Crear, guardar y publicar un asiento balanceado con cada tipo de diario.
- Confirmar que el diario permanece seleccionado después de guardar y reabrir.
- Revisar la numeración resultante, especialmente en diarios de ventas y compras.
- Confirmar que una factura de venta solo ofrece diarios de ventas y que una
  factura de proveedor solo ofrece diarios de compras.
- Registrar un pago y una transacción bancaria por sus flujos habituales.
- Comprobar la selección de diarios al cambiar de compañía y, si se utilizan,
  las sucursales y diarios en moneda extranjera.

## Pruebas y estado de validación

Se incluyen 8 pruebas de integración de Odoo, que cubren los seis tipos nativos,
guardado mediante formulario, publicación, selección por defecto, compañías,
diarios archivados, facturas/recibos, pagos/extractos y rechazo de descuadres.

Para ejecutarlas, instalar el módulo en una base de pruebas con el ejecutor de
Odoo y esta selección:

```text
odoo-bin -d BASE_DE_PRUEBAS -i account_manual_entry_any_journal --test-enable --test-tags /account_manual_entry_any_journal --stop-after-init
```

La configuración de Odoo debe incluir el directorio de módulos personalizados
en `addons_path`. En Odoo.sh también se pueden ejecutar mediante la compilación
de desarrollo con la instalación y las pruebas del módulo habilitadas.

Se revisaron las firmas y los puntos de extensión contra el código público de
Odoo 19.0 y se verificaron la sintaxis y la estructura del paquete. Las pruebas
de integración **no se han ejecutado**: este entorno no dispone de un servidor
Odoo ni una base PostgreSQL. Queda pendiente validar en Odoo.sh la interacción
con Enterprise, la localización fiscal y otros módulos de la instalación.

## Implementación y referencias

Extiende `account.move` por herencia, sin editar el código estándar ni reemplazar
vistas. Amplía `_get_valid_journal_types` y `_compute_suitable_journal_ids`, y
conserva la selección inicial de `_search_default_journal` mediante un contexto
interno limitado a esa búsqueda. No utiliza `sudo()` ni desactiva validaciones.

- [Modelo oficial de Odoo 19.0](https://github.com/odoo/odoo/blob/19.0/addons/account/models/account_move.py)
- [Formulario oficial de asientos](https://github.com/odoo/odoo/blob/19.0/addons/account/views/account_move_views.xml)
- [Despliegue de módulos en Odoo.sh](https://www.odoo.com/documentation/19.0/administration/odoo_sh/getting_started/first_module.html)

La rama pública 18.0 consultada también contiene restricciones similares; el
comportamiento puede variar según la versión anterior exacta y sus módulos.

Licencia: LGPL-3.
